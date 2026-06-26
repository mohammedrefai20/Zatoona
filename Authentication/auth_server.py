import logging
from datetime import datetime, timedelta

import uvicorn
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from Authentication.config import settings
from Authentication.database import Base, engine, get_db
from Authentication.models import User
from Authentication.security import (
    authenticate_user,
    get_current_user,
    get_password_hash,
    issue_token_pair,
    revoke_refresh_token_for_user,
    rotate_refresh_token,
    update_last_login,
    validate_refresh_token,
    create_access_token_for_user,
    generate_session_id,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("auth_server.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

app = FastAPI()
Base.metadata.create_all(bind=engine)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


@app.get("/health")
async def health_check():
    return {
        "status": "UP",
        "service": "auth-service",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/auth/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    update_last_login(db, user)
    return TokenResponse(**issue_token_pair(db, user))


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_tokens(body: RefreshRequest, db: Session = Depends(get_db)):
    user = validate_refresh_token(db, body.refresh_token)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token_for_user(user, access_token_expires)
    new_refresh_token = rotate_refresh_token(db, body.refresh_token, user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=int(access_token_expires.total_seconds()),
    )


@app.post("/auth/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    refresh_token: str = Form(None),
):
    if refresh_token:
        revoke_refresh_token_for_user(db, current_user, refresh_token)

    return {"message": "Successfully logged out"}


@app.post("/auth/signup")
async def signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=username,
        email=email,
        password=get_password_hash(password),
        session_id=generate_session_id(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}


@app.get("/auth/verify")
async def verify_token(request: Request, db: Session = Depends(get_db)):
    """
    Verifies the JWT access token from the Authorization header.
    Used by the Nginx auth_request directive to authenticate requests.
    """
    try:
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Must be 'Bearer {token}'",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = authorization.replace("Bearer ", "")
        current_user = await get_current_user(token, db)

        return {
            "authenticated": True,
            "username": current_user.username,
            "email": current_user.email,
            "user_id": current_user.id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from Authentication.config import settings
from Authentication.database import get_db
from Authentication.models import RefreshToken, User, StoredExam

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)
def get_exam_by_id(db: Session, exam_id: int, session_id: str) -> Optional[StoredExam]:
    return db.query(StoredExam).filter(StoredExam.exam_id == exam_id, StoredExam.session_id == session_id).first()

def get_exam_by_session_id(db: Session, session_id: str) -> Optional[StoredExam]:
    return db.query(StoredExam).filter(StoredExam.session_id == session_id).first()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_username_or_email(db: Session, identifier: str) -> Optional[User]:
    return (
        db.query(User)
        .filter((User.username == identifier) | (User.email == identifier))
        .first()
    )


def authenticate_user(db: Session, identifier: str, password: str) -> Optional[User]:
    user = get_user_by_username_or_email(db, identifier)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password):
        return None
    return user


def update_last_login(db: Session, user: User) -> None:
    user.last_login = datetime.utcnow()
    db.commit()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token_for_user(
    user: User, expires_delta: Optional[timedelta] = None
) -> str:
    return create_access_token(
        {
            "sub": user.username,
            "user_id": user.id,
            "email": user.email,
        },
        expires_delta=expires_delta,
    )
def generate_session_id() -> str:
    return str(uuid.uuid4())
def get_refresh_token(db: Session, token: str) -> Optional[RefreshToken]:
    return db.query(RefreshToken).filter(RefreshToken.token == token).first()


def create_refresh_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    expire_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db.add(
        RefreshToken(
            user_id=user.id,
            token=token,
            expire_at=expire_at,
        )
    )
    db.commit()
    return token


def issue_token_pair(db: Session, user: User) -> dict:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token_for_user(user, access_token_expires),
        "refresh_token": create_refresh_token(db, user),
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
    }


def revoke_refresh_token(db: Session, token: str) -> None:
    stored = get_refresh_token(db, token)
    if stored:
        db.delete(stored)
        db.commit()


def revoke_all_refresh_tokens_for_user(db: Session, user: User) -> None:
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
    db.commit()


def revoke_refresh_token_for_user(db: Session, user: User, token: str) -> None:
    stored = get_refresh_token(db, token)
    if stored and stored.user_id == user.id:
        db.delete(stored)
        db.commit()


def validate_refresh_token(db: Session, token: str) -> User:
    stored = get_refresh_token(db, token)
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if stored.expire_at < datetime.utcnow():
        db.delete(stored)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    user = stored.user or get_user_by_id(db, stored.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


def rotate_refresh_token(db: Session, old_token: str, user: User) -> str:
    revoke_refresh_token(db, old_token)
    return create_refresh_token(db, user)


def _decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def _user_from_token_payload(db: Session, payload: dict) -> Optional[User]:
    user_id = payload.get("user_id")
    if user_id is not None:
        return get_user_by_id(db, user_id)

    username = payload.get("sub")
    if username:
        return get_user_by_username(db, username)

    return None


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    payload = _decode_access_token(token)

    exp = payload.get("exp")
    if exp is None or datetime.utcfromtimestamp(exp) < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please refresh or login again",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = _user_from_token_payload(db, payload)
    if not user or not user.is_active:
        raise credentials_exception

    return user

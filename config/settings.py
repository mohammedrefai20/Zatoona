from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY      = os.getenv("GROQ_API_KEY")
MODEL_NAME        = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
USE_REAL_MCP      = os.getenv("USE_REAL_MCP", "false")
MCP_HOST          = os.getenv("MCP_SERVER_HOST", "localhost")
MCP_PORT          = int(os.getenv("MCP_SERVER_PORT", 8000))
USE_REAL_EXAM     = os.getenv("USE_REAL_EXAM", "false")
USE_REAL_ANSWERS  = os.getenv("USE_REAL_ANSWERS", "false")
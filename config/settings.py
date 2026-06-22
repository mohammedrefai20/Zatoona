from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")
MOCK_MCP_PATH = os.getenv(
    "MOCK_MCP_PATH",
    str(PROJECT_ROOT / "tests" / "team_b" / "mock_data" / "mock_mcp_response.json"),
)
MAX_VALIDATION_ITERATIONS = int(os.getenv("MAX_VALIDATION_ITERATIONS", "3"))

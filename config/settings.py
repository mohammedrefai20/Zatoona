from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BASE_URL = os.getenv("LIGHTNING_BASE_URL", "https://lightning.ai/api/v1/")
LIGHTNING_API_KEY = os.getenv("LIGHTNING_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")
MOCK_MCP_PATH = os.getenv(
    "MOCK_MCP_PATH",
    str(PROJECT_ROOT / "tests" / "team_b" / "mock_data" / "mock_mcp_response.json"),
)
MAX_VALIDATION_ITERATIONS = int(os.getenv("MAX_VALIDATION_ITERATIONS", "3"))

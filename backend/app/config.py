"""Environment configuration shared by backend modules."""

from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"


def load_environment() -> None:
    """Load backend/.env without overriding variables set in the shell."""
    load_dotenv(ENV_FILE, override=False)

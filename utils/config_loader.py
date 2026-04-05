import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None


def load_environment() -> None:
    """Load environment variables from .env when python-dotenv is installed."""
    if load_dotenv is not None:
        load_dotenv()


def get_required_env(name: str) -> str:
    """Read a required environment variable and fail fast if it is missing."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_optional_env(name: str, default: str | None = None) -> str | None:
    """Read an optional environment variable."""
    return os.getenv(name, default)

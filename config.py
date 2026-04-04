import os


def _get_required_env(name: str) -> str:
    """Read a required environment variable and fail fast if it is missing."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


BOT_TOKEN = _get_required_env("BOT_TOKEN")
AI_KEY = _get_required_env("AI_KEY")

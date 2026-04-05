import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


BOT_TOKEN = _required("BOT_TOKEN")
AI_KEY = _required("AI_KEY")
BINANCE_KEY = os.getenv("BINANCE_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET")
BYBIT_KEY = os.getenv("BYBIT_KEY")
BYBIT_SECRET = os.getenv("BYBIT_SECRET")

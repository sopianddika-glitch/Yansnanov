from utils.config_loader import get_optional_env, get_required_env, load_environment

load_environment()

BOT_TOKEN = get_required_env("BOT_TOKEN")
AI_KEY = get_required_env("AI_KEY")

BINANCE_KEY = get_optional_env("BINANCE_KEY")
BINANCE_SECRET = get_optional_env("BINANCE_SECRET")
BYBIT_KEY = get_optional_env("BYBIT_KEY")
BYBIT_SECRET = get_optional_env("BYBIT_SECRET")
NEWS_API_KEY = get_optional_env("NEWS_API_KEY")
APP_TIMEZONE = get_optional_env("APP_TIMEZONE", "UTC")

from services.data_binance import binance_data_source
from utils.logger import get_logger

logger = get_logger(__name__)


class BinanceService:
    """Binance REST wrapper used by handlers and higher-level services."""

    async def get_price(self, symbol: str) -> dict:
        """Fetch the latest Binance spot price and basic metadata."""
        context = await binance_data_source.get_market_context(symbol, interval="1h", limit=3)
        ticker = context["ticker"]
        return {
            "symbol": context["symbol"],
            "pair": context["pair"],
            "price": ticker["last_price"],
            "price_change_pct": ticker["price_change_pct"],
            "volume": ticker["volume"],
            "source": "binance",
        }

    async def get_market_context(self, symbol: str, interval: str = "1h", limit: int = 250) -> dict:
        """Expose richer Binance market context for analysis modules."""
        return await binance_data_source.get_market_context(symbol, interval=interval, limit=limit)


binance_service = BinanceService()

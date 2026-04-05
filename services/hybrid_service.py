import asyncio

from services.binance_service import binance_service
from services.bybit_service import bybit_service
from utils.logger import get_logger

logger = get_logger(__name__)


class HybridMarketService:
    """Unify Binance and Bybit market snapshots into one response."""

    async def get_hybrid_price(self, symbol: str) -> dict:
        """Fetch primary and secondary prices plus spread information."""
        binance_quote, bybit_quote = await asyncio.gather(
            binance_service.get_price(symbol),
            bybit_service.get_price(symbol),
            return_exceptions=True,
        )

        quotes = [quote for quote in (binance_quote, bybit_quote) if isinstance(quote, dict)]
        if not quotes:
            raise RuntimeError("No exchange quote is available right now.")

        primary = quotes[0]
        secondary = quotes[1] if len(quotes) > 1 else quotes[0]
        spread_abs = primary["price"] - secondary["price"]
        spread_pct = (spread_abs / secondary["price"] * 100) if secondary["price"] else 0.0

        return {
            "symbol": primary["symbol"],
            "price": primary["price"],
            "exchange_primary": primary["source"],
            "exchange_secondary": secondary["source"],
            "spread_info": {
                "primary_price": primary["price"],
                "secondary_price": secondary["price"],
                "spread_abs": spread_abs,
                "spread_pct": spread_pct,
            },
        }


hybrid_service = HybridMarketService()

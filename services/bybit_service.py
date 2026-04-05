import asyncio

import requests

from services.data_bybit import bybit_data_source
from utils.logger import get_logger

logger = get_logger(__name__)
BYBIT_TICKER_URL = "https://api.bybit.com/v5/market/tickers"


class BybitService:
    """Bybit REST wrapper for price and futures metrics."""

    async def get_price(self, symbol: str) -> dict:
        """Fetch the latest Bybit linear futures price."""
        return await asyncio.to_thread(self._get_price_sync, symbol)

    async def get_futures_context(self, symbol: str, interval: str = "1h") -> dict:
        """Expose Bybit futures context."""
        normalized_symbol = self.normalize_symbol(symbol)
        pair = f"{normalized_symbol}USDT"
        return await bybit_data_source.get_futures_context(pair, interval=interval)

    def _get_price_sync(self, symbol: str) -> dict:
        normalized_symbol = self.normalize_symbol(symbol)
        pair = f"{normalized_symbol}USDT"

        try:
            response = requests.get(
                BYBIT_TICKER_URL,
                params={"category": "linear", "symbol": pair},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.exception("Failed to fetch Bybit ticker for %s", pair)
            raise RuntimeError("Unable to reach Bybit right now.") from exc

        if payload.get("retCode") != 0:
            raise RuntimeError(payload.get("retMsg", "Bybit request failed."))

        items = payload.get("result", {}).get("list", [])
        if not items:
            raise RuntimeError(f"No Bybit ticker data returned for {pair}.")

        item = items[0]
        return {
            "symbol": normalized_symbol,
            "pair": pair,
            "price": float(item["lastPrice"]),
            "price_change_pct": float(item.get("price24hPcnt", 0.0)) * 100,
            "volume": float(item.get("volume24h", 0.0)),
            "source": "bybit",
        }

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper().replace("/", "").replace("-", "")
        if not normalized:
            raise ValueError("Please provide a valid symbol.")
        if normalized.endswith("USDT"):
            normalized = normalized[:-4]
        return normalized


bybit_service = BybitService()

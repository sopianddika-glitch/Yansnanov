import asyncio
import logging

import requests

logger = logging.getLogger(__name__)
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"


class MarketService:
    """Service wrapper around the Binance public ticker API."""

    async def get_price(self, symbol: str) -> tuple[str, float]:
        """Fetch a USDT pair price without blocking the event loop."""
        return await asyncio.to_thread(self._get_price_sync, symbol)

    def _get_price_sync(self, symbol: str) -> tuple[str, float]:
        """Fetch and validate a price response from Binance."""
        normalized = self._normalize_symbol(symbol)
        pair = f"{normalized}USDT"

        try:
            response = requests.get(
                BINANCE_TICKER_URL,
                params={"symbol": pair},
                timeout=10,
            )
        except requests.RequestException as exc:
            logger.exception("Failed to reach Binance API.")
            raise RuntimeError("The market service is temporarily unavailable. Please try again later.") from exc

        if response.status_code == 400:
            raise ValueError(f"Unknown market symbol: {normalized}")

        try:
            response.raise_for_status()
            payload = response.json()
            price = float(payload["price"])
        except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
            logger.exception("Invalid response received from Binance.")
            raise RuntimeError("Failed to read the latest market price. Please try again later.") from exc

        return pair, price

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Normalize user input into a Binance-compatible base asset symbol."""
        cleaned_symbol = symbol.strip().upper().replace("/", "").replace("-", "")
        if not cleaned_symbol:
            raise ValueError("Please provide a valid symbol, for example: /price BTC")
        if cleaned_symbol.endswith("USDT"):
            cleaned_symbol = cleaned_symbol[:-4]
        return cleaned_symbol


market_service = MarketService()

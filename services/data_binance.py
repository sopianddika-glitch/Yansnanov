import asyncio
import logging

import requests

logger = logging.getLogger(__name__)
BINANCE_BASE_URL = "https://api.binance.com"


class BinanceMarketDataSource:
    """Spot market data adapter for Binance."""

    async def get_market_context(self, symbol: str, interval: str = "1h", limit: int = 250) -> dict:
        """Fetch ticker and kline data for analysis."""
        normalized_symbol = self.normalize_symbol(symbol)
        pair = f"{normalized_symbol}USDT"

        ticker_task = asyncio.to_thread(self._get_ticker_24h, pair)
        klines_task = asyncio.to_thread(self._get_klines, pair, interval, limit)
        ticker, candles = await asyncio.gather(ticker_task, klines_task)

        return {
            "symbol": normalized_symbol,
            "pair": pair,
            "ticker": ticker,
            "candles": candles,
        }

    def _get_ticker_24h(self, pair: str) -> dict:
        response = self._request(
            "/api/v3/ticker/24hr",
            params={"symbol": pair},
        )

        return {
            "last_price": float(response["lastPrice"]),
            "price_change_pct": float(response["priceChangePercent"]),
            "high_price": float(response["highPrice"]),
            "low_price": float(response["lowPrice"]),
            "volume": float(response["volume"]),
            "quote_volume": float(response["quoteVolume"]),
            "count": int(response["count"]),
        }

    def _get_klines(self, pair: str, interval: str, limit: int) -> list[dict[str, float]]:
        response = self._request(
            "/api/v3/klines",
            params={"symbol": pair, "interval": interval, "limit": limit},
        )

        candles = []
        for row in response:
            candles.append(
                {
                    "open_time": int(row[0]),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                    "close_time": int(row[6]),
                    "quote_volume": float(row[7]),
                    "trade_count": float(row[8]),
                    "taker_buy_base_volume": float(row[9]),
                    "taker_buy_quote_volume": float(row[10]),
                }
            )

        if not candles:
            raise RuntimeError(f"Binance returned no candle data for {pair}.")

        return candles

    def _request(self, path: str, params: dict) -> dict | list:
        url = f"{BINANCE_BASE_URL}{path}"

        try:
            response = requests.get(url, params=params, timeout=15)
        except requests.RequestException as exc:
            logger.exception("Binance request failed for %s", path)
            raise RuntimeError("Unable to reach Binance right now.") from exc

        if response.status_code == 400:
            raise ValueError(f"Unknown market symbol: {params.get('symbol', '')}")

        try:
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.exception("Invalid Binance response for %s", path)
            raise RuntimeError("Binance returned an invalid response.") from exc

        return payload

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """Normalize user input to a base asset symbol."""
        normalized = symbol.strip().upper().replace("/", "").replace("-", "")
        if not normalized:
            raise ValueError("Please provide a valid symbol.")
        if normalized.endswith("USDT"):
            normalized = normalized[:-4]
        return normalized


binance_data_source = BinanceMarketDataSource()

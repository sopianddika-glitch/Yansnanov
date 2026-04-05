import asyncio

import requests

from utils.logger import get_logger

logger = get_logger(__name__)
BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"
BINANCE_24H_URL = "https://api.binance.com/api/v3/ticker/24hr"
BYBIT_TICKER_URL = "https://api.bybit.com/v5/market/tickers"
DEFAULT_SCAN_SYMBOLS = ("BTC", "ETH", "SOL", "BNB", "XRP")


class MarketService:
    async def get_price(self, symbol: str) -> dict:
        return await asyncio.to_thread(self._get_price_sync, symbol)

    async def get_market_snapshot(self, symbol: str) -> dict:
        return await asyncio.to_thread(self._get_market_snapshot_sync, symbol)

    async def scan_market(self, symbols: tuple[str, ...] | None = None) -> list[dict]:
        scan_symbols = symbols or DEFAULT_SCAN_SYMBOLS
        snapshots = await asyncio.gather(
            *(self.get_market_snapshot(symbol) for symbol in scan_symbols),
            return_exceptions=True,
        )
        results = [item for item in snapshots if isinstance(item, dict)]
        results.sort(key=lambda item: abs(item["change_percent"]), reverse=True)
        return results

    def format_price_text(self, quote: dict) -> str:
        lines = [
            "Price",
            f"Instrument: {quote['pair']}",
            f"Primary Exchange: {quote['exchange_primary']}",
            f"Last Price: {self._fmt(quote['price'])}",
        ]
        if quote["exchange_secondary"]:
            lines.append(f"Secondary Exchange: {quote['exchange_secondary']}")
            lines.append(f"Secondary Price: {self._fmt(quote['secondary_price'])}")
            lines.append(f"Spread: {quote['spread_percent']:+.4f}%")
        return "\n".join(lines)

    def format_market_text(self, snapshot: dict) -> str:
        return "\n".join(
            [
                "Market",
                f"Instrument: {snapshot['pair']}",
                f"Last Price: {self._fmt(snapshot['price'])}",
                f"24h Change: {snapshot['change_percent']:+.2f}%",
                f"24h High: {self._fmt(snapshot['high_price'])}",
                f"24h Low: {self._fmt(snapshot['low_price'])}",
                f"24h Volume: {snapshot['volume']:,.2f}",
                f"Bias: {snapshot['bias']}",
                f"Confidence: {snapshot['confidence']:.0f}/100",
            ]
        )

    def format_signal_text(self, snapshot: dict) -> str:
        return "\n".join(
            [
                "Signal",
                f"Instrument: {snapshot['pair']}",
                f"Bias: {snapshot['bias']}",
                f"Confidence: {snapshot['confidence']:.0f}/100",
                f"Price Change: {snapshot['change_percent']:+.2f}%",
                f"Spread Monitor: {snapshot['spread_percent']:+.4f}%",
                f"Takeaway: {self._signal_takeaway(snapshot)}",
            ]
        )

    def format_summary_context(self, snapshot: dict) -> str:
        return "\n".join(
            [
                f"Instrument: {snapshot['pair']}",
                f"Last price: {self._fmt(snapshot['price'])}",
                f"24h change: {snapshot['change_percent']:+.2f}%",
                f"24h high: {self._fmt(snapshot['high_price'])}",
                f"24h low: {self._fmt(snapshot['low_price'])}",
                f"24h volume: {snapshot['volume']:,.2f}",
                f"Primary exchange: {snapshot['exchange_primary']}",
                f"Secondary exchange: {snapshot['exchange_secondary'] or 'Unavailable'}",
                f"Spread percent: {snapshot['spread_percent']:+.4f}%",
                f"Bias: {snapshot['bias']}",
                f"Confidence: {snapshot['confidence']:.0f}/100",
            ]
        )

    def format_fallback_summary(self, snapshot: dict) -> str:
        return "\n".join(
            [
                "Summary",
                f"{snapshot['pair']} remains {snapshot['bias'].lower()} with confidence "
                f"{snapshot['confidence']:.0f}/100.",
                f"The market moved {snapshot['change_percent']:+.2f}% over the last 24 hours "
                f"between {self._fmt(snapshot['low_price'])} and {self._fmt(snapshot['high_price'])}.",
                f"Current cross-exchange spread is {snapshot['spread_percent']:+.4f}%.",
            ]
        )

    def format_report_text(self, snapshot: dict, ai_text: str | None = None) -> str:
        lines = [
            "Market Report",
            "",
            "Price Action",
            f"- Instrument: {snapshot['pair']}",
            f"- Last Price: {self._fmt(snapshot['price'])}",
            f"- 24h Change: {snapshot['change_percent']:+.2f}%",
            f"- 24h Range: {self._fmt(snapshot['low_price'])} to {self._fmt(snapshot['high_price'])}",
            "",
            "Execution Context",
            f"- Primary Exchange: {snapshot['exchange_primary']}",
            f"- Secondary Exchange: {snapshot['exchange_secondary'] or 'Unavailable'}",
            f"- Cross-Exchange Spread: {snapshot['spread_percent']:+.4f}%",
            "",
            "Signal",
            f"- Bias: {snapshot['bias']}",
            f"- Confidence: {snapshot['confidence']:.0f}/100",
            f"- Read: {self._signal_takeaway(snapshot)}",
        ]
        if ai_text:
            lines.extend(["", "AI Note", ai_text.strip()])
        return "\n".join(lines)

    def format_scan_text(self, snapshots: list[dict]) -> str:
        if not snapshots:
            return "Scan\nNo market data is available right now."
        lines = ["Scan"]
        for snapshot in snapshots:
            lines.append(
                f"- {snapshot['pair']}: {snapshot['bias']} | "
                f"{snapshot['change_percent']:+.2f}% | "
                f"confidence {snapshot['confidence']:.0f}/100"
            )
        return "\n".join(lines)

    def _get_price_sync(self, symbol: str) -> dict:
        normalized = self._normalize_symbol(symbol)
        pair = f"{normalized}USDT"
        binance_payload = self._request_json(BINANCE_PRICE_URL, {"symbol": pair})
        bybit_payload = self._safe_request_json(
            BYBIT_TICKER_URL, {"category": "linear", "symbol": pair}
        )
        primary_price = float(binance_payload["price"])
        secondary_price = self._extract_bybit_price(bybit_payload)
        spread_percent = self._spread_percent(primary_price, secondary_price)
        return {
            "symbol": normalized,
            "pair": pair,
            "price": primary_price,
            "exchange_primary": "Binance",
            "exchange_secondary": "Bybit" if secondary_price is not None else None,
            "secondary_price": secondary_price,
            "spread_percent": spread_percent,
        }

    def _get_market_snapshot_sync(self, symbol: str) -> dict:
        quote = self._get_price_sync(symbol)
        ticker = self._request_json(BINANCE_24H_URL, {"symbol": quote["pair"]})
        price = quote["price"]
        high_price = float(ticker["highPrice"])
        low_price = float(ticker["lowPrice"])
        change_percent = float(ticker["priceChangePercent"])
        weighted_avg = float(ticker["weightedAvgPrice"])
        confidence = self._confidence(change_percent, quote["spread_percent"])
        return {
            **quote,
            "high_price": high_price,
            "low_price": low_price,
            "volume": float(ticker["volume"]),
            "quote_volume": float(ticker["quoteVolume"]),
            "weighted_avg_price": weighted_avg,
            "change_percent": change_percent,
            "bias": self._bias(change_percent),
            "confidence": confidence,
            "deviation_percent": self._deviation_percent(price, weighted_avg),
        }

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        cleaned = symbol.strip().upper().replace("/", "").replace("-", "")
        if cleaned.endswith("USDT"):
            cleaned = cleaned[:-4]
        if not cleaned:
            raise ValueError("Please provide a symbol such as BTC or ETH.")
        return cleaned

    @staticmethod
    def _request_json(url: str, params: dict) -> dict:
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise RuntimeError("The market data service is temporarily unavailable.") from exc

    def _safe_request_json(self, url: str, params: dict) -> dict | None:
        try:
            return self._request_json(url, params)
        except RuntimeError:
            logger.warning("Secondary exchange request failed for params %s", params)
            return None

    @staticmethod
    def _extract_bybit_price(payload: dict | None) -> float | None:
        if not payload:
            return None
        result = payload.get("result", {})
        items = result.get("list") or []
        if not items:
            return None
        last_price = items[0].get("lastPrice")
        return float(last_price) if last_price else None

    @staticmethod
    def _spread_percent(primary: float, secondary: float | None) -> float:
        if secondary is None or primary == 0:
            return 0.0
        return ((secondary - primary) / primary) * 100

    @staticmethod
    def _deviation_percent(price: float, weighted_avg: float) -> float:
        if weighted_avg == 0:
            return 0.0
        return ((price - weighted_avg) / weighted_avg) * 100

    @staticmethod
    def _bias(change_percent: float) -> str:
        if change_percent >= 1.5:
            return "Bullish"
        if change_percent <= -1.5:
            return "Bearish"
        return "Neutral"

    @staticmethod
    def _confidence(change_percent: float, spread_percent: float) -> float:
        confidence = 55 + min(abs(change_percent) * 7, 35)
        confidence -= min(abs(spread_percent) * 5, 15)
        return max(35.0, min(confidence, 95.0))

    @staticmethod
    def _signal_takeaway(snapshot: dict) -> str:
        if snapshot["bias"] == "Bullish":
            return "Momentum favors continuation while price holds near the upper half of the daily range."
        if snapshot["bias"] == "Bearish":
            return "Pressure remains defensive and traders should watch for follow-through below the daily midpoint."
        return "The market is balanced and may require a breakout before conviction improves."

    @staticmethod
    def _fmt(value: float | None) -> str:
        if value is None:
            return "Unavailable"
        return f"{value:,.6f}".rstrip("0").rstrip(".")


market_service = MarketService()

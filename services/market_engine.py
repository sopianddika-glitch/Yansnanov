import asyncio
import logging
from dataclasses import dataclass
from typing import Protocol

from services.data_binance import binance_data_source
from services.data_bybit import bybit_data_source
from services.indicators import (
    composite_signal,
    evaluate_momentum,
    evaluate_structure,
    evaluate_trend,
    evaluate_volatility,
    evaluate_volume,
)

logger = logging.getLogger(__name__)
DEFAULT_SCAN_SYMBOLS = ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE")


class SpotDataProvider(Protocol):
    async def get_market_context(self, symbol: str, interval: str = "1h", limit: int = 250) -> dict: ...


class FuturesDataProvider(Protocol):
    async def get_futures_context(self, pair: str, interval: str = "1h") -> dict: ...


@dataclass(slots=True)
class MarketAnalysis:
    symbol: str
    pair: str
    interval: str
    last_price: float
    price_change_24h: float
    high_price_24h: float
    low_price_24h: float
    volume_24h: float
    quote_volume_24h: float
    trade_count_24h: int
    trend: dict
    momentum: dict
    volatility: dict
    volume: dict
    structure: dict
    futures: dict
    signal: dict


class MarketEngine:
    """Orchestrates raw market data and indicator calculations."""

    def __init__(self, spot_provider: SpotDataProvider, futures_provider: FuturesDataProvider) -> None:
        self._spot_provider = spot_provider
        self._futures_provider = futures_provider

    async def analyze_symbol(self, symbol: str, interval: str = "1h", limit: int = 250) -> MarketAnalysis:
        """Build a full market intelligence snapshot for one symbol."""
        spot_context = await self._spot_provider.get_market_context(symbol, interval, limit)
        futures_context = await self._futures_provider.get_futures_context(spot_context["pair"], interval)

        candles = spot_context["candles"]
        closes = [candle["close"] for candle in candles]

        trend = evaluate_trend(closes)
        momentum = evaluate_momentum(closes)
        volatility = evaluate_volatility(candles)
        volume = evaluate_volume(candles)
        structure = evaluate_structure(candles, spot_context["ticker"]["last_price"])
        signal = composite_signal(
            trend=trend,
            momentum=momentum,
            volatility=volatility,
            volume=volume,
            futures=futures_context,
            price_change_24h=spot_context["ticker"]["price_change_pct"],
        )

        ticker = spot_context["ticker"]

        return MarketAnalysis(
            symbol=spot_context["symbol"],
            pair=spot_context["pair"],
            interval=interval,
            last_price=ticker["last_price"],
            price_change_24h=ticker["price_change_pct"],
            high_price_24h=ticker["high_price"],
            low_price_24h=ticker["low_price"],
            volume_24h=ticker["volume"],
            quote_volume_24h=ticker["quote_volume"],
            trade_count_24h=ticker["count"],
            trend=trend,
            momentum=momentum,
            volatility=volatility,
            volume=volume,
            structure=structure,
            futures=futures_context,
            signal=signal,
        )

    async def scan_market(self, symbols: list[str] | None = None, interval: str = "1h") -> list[MarketAnalysis]:
        """Run the market engine across a watchlist and sort by signal confidence."""
        scan_list = symbols or list(DEFAULT_SCAN_SYMBOLS)
        tasks = [self._safe_analyze(symbol, interval) for symbol in scan_list]
        results = await asyncio.gather(*tasks)
        analyses = [analysis for analysis in results if analysis is not None]
        analyses.sort(key=lambda item: float(item.signal["confidence"]), reverse=True)
        return analyses

    async def _safe_analyze(self, symbol: str, interval: str) -> MarketAnalysis | None:
        try:
            return await self.analyze_symbol(symbol, interval=interval)
        except Exception as exc:
            logger.warning("Skipping %s during market scan: %s", symbol, exc)
            return None


market_engine = MarketEngine(
    spot_provider=binance_data_source,
    futures_provider=bybit_data_source,
)

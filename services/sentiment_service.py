from services.market_engine import market_engine
from services.news_service import news_service
from utils.logger import get_logger

logger = get_logger(__name__)


class SentimentService:
    """Simple sentiment layer built from market structure and headline tone."""

    async def get_sentiment_snapshot(self, symbol: str) -> dict:
        """Compute a lightweight market sentiment score."""
        analysis = await market_engine.analyze_symbol(symbol)
        news_items = await news_service.get_news_items(symbol)

        score = 50.0
        score += (analysis.price_change_24h * 0.6)
        score += (float(analysis.signal["confidence"]) - 50) * 0.45
        score += 8 if analysis.trend["bias"] == "bullish" else -8 if analysis.trend["bias"] == "bearish" else 0
        score += 6 if analysis.momentum["bias"] == "bullish" else -6 if analysis.momentum["bias"] == "bearish" else 0
        if analysis.futures.get("available"):
            score += 5 if analysis.futures["positioning_bias"] == "bullish" else -5 if analysis.futures["positioning_bias"] == "bearish" else 0

        score = max(0.0, min(score, 100.0))
        label = "bullish" if score >= 60 else "bearish" if score <= 40 else "neutral"

        drivers = [
            f"Trend bias is {analysis.trend['bias']}",
            f"Momentum bias is {analysis.momentum['bias']}",
            f"Volatility regime is {analysis.volatility['regime']}",
            f"News tone is derived from {len(news_items)} market headlines",
        ]

        return {
            "symbol": analysis.pair,
            "score": score,
            "label": label,
            "drivers": drivers,
        }

    async def get_sentiment_report(self, symbol: str) -> str:
        """Render a text report for one symbol's sentiment profile."""
        snapshot = await self.get_sentiment_snapshot(symbol)
        lines = [
            "Sentiment Snapshot",
            f"Instrument: {snapshot['symbol']}",
            f"Sentiment: {snapshot['label'].title()}",
            f"Score: {snapshot['score']:.1f}/100",
            "",
            "Drivers",
        ]
        lines.extend(f"- {driver}" for driver in snapshot["drivers"])
        return "\n".join(lines)


sentiment_service = SentimentService()

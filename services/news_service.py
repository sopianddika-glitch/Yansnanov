from services.market_engine import market_engine
from utils.cache import TTLCache
from utils.logger import get_logger

logger = get_logger(__name__)
news_cache = TTLCache(ttl_seconds=300)


class NewsService:
    """Clean news interface with a synthetic fallback until live APIs are wired in."""

    async def get_news_items(self, symbol: str | None = None) -> list[dict]:
        """Return a small news list suitable for Telegram display."""
        cache_key = f"news:{symbol or 'market'}"
        cached = news_cache.get(cache_key)
        if cached is not None:
            return cached

        target_symbol = symbol or "BTC"
        analysis = await market_engine.analyze_symbol(target_symbol)

        # TODO: Replace these synthetic headlines with a real news provider API.
        items = [
            {
                "title": f"{analysis.pair} market tone is {analysis.signal['bias']} with confidence at {analysis.signal['confidence']:.1f}/100",
                "source": "internal-market-model",
            },
            {
                "title": f"Trend is {analysis.trend['bias']} while momentum reads {analysis.momentum['bias']}; volatility is {analysis.volatility['regime']}",
                "source": "internal-market-model",
            },
            {
                "title": f"Volume flow shows {analysis.volume['flow_state']} and futures positioning is {analysis.futures.get('positioning_bias', 'unavailable')}",
                "source": "internal-market-model",
            },
        ]

        news_cache.set(cache_key, items)
        return items

    async def get_news_brief(self, symbol: str | None = None) -> str:
        """Render news items into a Telegram-friendly brief."""
        target = symbol or "market"
        items = await self.get_news_items(symbol)
        lines = [
            "News Brief",
            f"Scope: {target.upper()}",
            "",
        ]
        lines.extend(f"- {item['title']} ({item['source']})" for item in items)
        return "\n".join(lines)


news_service = NewsService()

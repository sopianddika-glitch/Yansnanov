import asyncio
import logging

import requests

logger = logging.getLogger(__name__)
BYBIT_BASE_URL = "https://api.bybit.com"
VALID_INTERVALS = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1d"}


class BybitFuturesDataSource:
    """Futures positioning and funding adapter for Bybit."""

    async def get_futures_context(self, pair: str, interval: str = "1h") -> dict:
        """Fetch open interest, funding, and long-short ratio."""
        mapped_interval = VALID_INTERVALS.get(interval, "1h")

        try:
            open_interest_task = asyncio.to_thread(self._get_open_interest, pair, mapped_interval)
            funding_task = asyncio.to_thread(self._get_funding_rate, pair)
            long_short_task = asyncio.to_thread(self._get_long_short_ratio, pair, mapped_interval)
            open_interest, funding, long_short = await asyncio.gather(
                open_interest_task,
                funding_task,
                long_short_task,
            )
        except ValueError:
            raise
        except RuntimeError as exc:
            logger.warning("Bybit futures metrics unavailable for %s: %s", pair, exc)
            return {
                "available": False,
                "reason": str(exc),
            }

        oi_current = open_interest["current"]
        oi_previous = open_interest["previous"]
        funding_rate = funding["current"]
        funding_previous = funding["previous"]
        buy_ratio = long_short["buy_ratio"]
        sell_ratio = long_short["sell_ratio"]
        long_short_ratio = buy_ratio / sell_ratio if sell_ratio else 0.0

        if funding_rate > 0.0001:
            funding_bias = "longs paying"
        elif funding_rate < -0.0001:
            funding_bias = "shorts paying"
        else:
            funding_bias = "neutral"

        if long_short_ratio > 1.05:
            positioning_bias = "bullish"
        elif long_short_ratio < 0.95:
            positioning_bias = "bearish"
        else:
            positioning_bias = "neutral"

        return {
            "available": True,
            "oi_current": oi_current,
            "oi_previous": oi_previous,
            "oi_delta": oi_current - oi_previous,
            "oi_delta_pct": _percent_change(oi_current, oi_previous),
            "funding_rate": funding_rate,
            "funding_previous": funding_previous,
            "funding_bias": funding_bias,
            "buy_ratio": buy_ratio * 100,
            "sell_ratio": sell_ratio * 100,
            "long_short_ratio": long_short_ratio,
            "positioning_bias": positioning_bias,
        }

    def _get_open_interest(self, pair: str, interval: str) -> dict:
        payload = self._request(
            "/v5/market/open-interest",
            params={
                "category": "linear",
                "symbol": pair,
                "intervalTime": interval,
                "limit": 2,
            },
        )

        items = payload["result"]["list"]
        if len(items) < 2:
            raise RuntimeError("Bybit open interest history is incomplete.")

        return {
            "current": float(items[0]["openInterest"]),
            "previous": float(items[1]["openInterest"]),
        }

    def _get_funding_rate(self, pair: str) -> dict:
        payload = self._request(
            "/v5/market/funding/history",
            params={
                "category": "linear",
                "symbol": pair,
                "limit": 2,
            },
        )

        items = payload["result"]["list"]
        if not items:
            raise RuntimeError("Bybit funding history is unavailable.")

        current = float(items[0]["fundingRate"])
        previous = float(items[1]["fundingRate"]) if len(items) > 1 else current

        return {
            "current": current,
            "previous": previous,
        }

    def _get_long_short_ratio(self, pair: str, period: str) -> dict:
        payload = self._request(
            "/v5/market/account-ratio",
            params={
                "category": "linear",
                "symbol": pair,
                "period": period,
                "limit": 2,
            },
        )

        items = payload["result"]["list"]
        if not items:
            raise RuntimeError("Bybit long-short ratio is unavailable.")

        return {
            "buy_ratio": float(items[0]["buyRatio"]),
            "sell_ratio": float(items[0]["sellRatio"]),
        }

    def _request(self, path: str, params: dict) -> dict:
        url = f"{BYBIT_BASE_URL}{path}"

        try:
            response = requests.get(url, params=params, timeout=15)
        except requests.RequestException as exc:
            logger.exception("Bybit request failed for %s", path)
            raise RuntimeError("Unable to reach Bybit right now.") from exc

        try:
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.exception("Invalid Bybit response for %s", path)
            raise RuntimeError("Bybit returned an invalid response.") from exc

        if payload.get("retCode") != 0:
            raise RuntimeError(payload.get("retMsg", "Bybit request failed."))

        return payload


def _percent_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


bybit_data_source = BybitFuturesDataSource()

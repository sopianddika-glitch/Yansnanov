from dataclasses import dataclass
from statistics import median

from services.indicators import atr, ema, evaluate_trend, macd, percent_change, rsi
from services.market_engine import MarketAnalysis

ALERT_CATEGORIES = {
    "price",
    "volume",
    "volatility",
    "trend",
    "momentum",
    "futures",
    "composite",
}

ALERT_RULE_TYPES = {
    "breakout",
    "breakdown",
    "sudden_move",
    "deviation",
    "volume_spike",
    "volume_divergence",
    "atr_expansion",
    "volatility_compression",
    "squeeze_release",
    "ema20_50_cross",
    "ema50_200_cross",
    "trend_reversal",
    "rsi_overbought",
    "rsi_oversold",
    "macd_crossover",
    "macd_divergence",
    "open_interest_spike",
    "funding_rate_flip",
    "long_short_imbalance",
    "multi_signal_confirmation",
}


@dataclass(slots=True)
class AlertEvent:
    category: str
    rule_type: str
    bias: str
    severity: str
    title: str
    detail: str

    @property
    def signature(self) -> str:
        """Stable dedupe key for scheduler deliveries."""
        return f"{self.category}:{self.rule_type}:{self.bias}:{self.severity}"


def evaluate_alerts(analysis: MarketAnalysis) -> list[AlertEvent]:
    """Evaluate all alert rules for a market analysis snapshot."""
    candles = analysis.candles
    if len(candles) < 60:
        return []

    closes = [candle["close"] for candle in candles]
    last_close = closes[-1]
    previous_close = closes[-2]
    last_move_pct = percent_change(last_close, previous_close)
    move_series = [abs(percent_change(closes[index], closes[index - 1])) for index in range(1, len(closes))]
    recent_move_baseline = median(move_series[-21:-1]) if len(move_series) > 21 else median(move_series)

    ema20_series = ema(closes, 20)
    ema50_series = ema(closes, 50)
    ema200_series = ema(closes, 200)
    rsi_series = rsi(closes, 14)
    macd_series = macd(closes)
    atr_series = atr(candles, 14)
    previous_trend = evaluate_trend(closes[:-1])

    current_ema20 = ema20_series[-1]
    current_ema50 = ema50_series[-1]
    current_ema200 = ema200_series[-1]
    previous_ema20 = ema20_series[-2]
    previous_ema50 = ema50_series[-2]
    previous_ema200 = ema200_series[-2]

    current_macd = macd_series["macd"][-1]
    previous_macd = macd_series["macd"][-2]
    current_signal = macd_series["signal"][-1]
    previous_signal = macd_series["signal"][-2]
    current_rsi = rsi_series[-1]
    current_atr = atr_series[-1]
    atr_recent_baseline = median(atr_series[-21:-1]) if len(atr_series) > 21 else median(atr_series)
    previous_atr_baseline = median(atr_series[-22:-2]) if len(atr_series) > 22 else atr_recent_baseline
    current_atr_ratio = current_atr / atr_recent_baseline if atr_recent_baseline else 1.0
    previous_atr_ratio = atr_series[-2] / previous_atr_baseline if previous_atr_baseline else 1.0

    alerts: list[AlertEvent] = []

    nearest_support = analysis.structure["nearest_support"]
    nearest_resistance = analysis.structure["nearest_resistance"]

    if nearest_resistance and previous_close <= nearest_resistance and last_close > nearest_resistance * 1.001:
        distance = percent_change(last_close, nearest_resistance)
        alerts.append(
            AlertEvent(
                category="price",
                rule_type="breakout",
                bias="bullish",
                severity="high" if distance >= 0.8 else "medium",
                title="Breakout",
                detail=f"Price closed above resistance at {nearest_resistance:,.4f} and is now {distance:+.2f}% beyond that level.",
            )
        )

    if nearest_support and previous_close >= nearest_support and last_close < nearest_support * 0.999:
        distance = percent_change(last_close, nearest_support)
        alerts.append(
            AlertEvent(
                category="price",
                rule_type="breakdown",
                bias="bearish",
                severity="high" if abs(distance) >= 0.8 else "medium",
                title="Breakdown",
                detail=f"Price closed below support at {nearest_support:,.4f} and is now {distance:+.2f}% from that level.",
            )
        )

    sudden_move_threshold = max(2.0, recent_move_baseline * 2.5)
    if abs(last_move_pct) >= sudden_move_threshold:
        alerts.append(
            AlertEvent(
                category="price",
                rule_type="sudden_move",
                bias="bullish" if last_move_pct > 0 else "bearish",
                severity="high" if abs(last_move_pct) >= 4 else "medium",
                title="Sudden Move",
                detail=f"Latest candle moved {last_move_pct:+.2f}% versus a recent baseline of {recent_move_baseline:.2f}%.",
            )
        )

    deviation_pct = percent_change(last_close, current_ema20)
    deviation_threshold = max(analysis.volatility["atr_pct"] * 2, 3.0)
    if abs(deviation_pct) >= deviation_threshold:
        alerts.append(
            AlertEvent(
                category="price",
                rule_type="deviation",
                bias="bullish" if deviation_pct > 0 else "bearish",
                severity="medium" if abs(deviation_pct) < 6 else "high",
                title="Price Deviation",
                detail=f"Price is {deviation_pct:+.2f}% away from EMA20, exceeding the alert threshold of {deviation_threshold:.2f}%.",
            )
        )

    if analysis.volume["volume_ratio"] >= 1.8:
        alerts.append(
            AlertEvent(
                category="volume",
                rule_type="volume_spike",
                bias="bullish" if analysis.volume["pressure_score"] >= 0 else "bearish",
                severity="high" if analysis.volume["volume_ratio"] >= 2.5 else "medium",
                title="Volume Spike",
                detail=f"Current volume is running at {analysis.volume['volume_ratio']:.2f}x the 20-bar average with flow showing {analysis.volume['flow_state']}.",
            )
        )

    if abs(last_move_pct) >= 1.2 and analysis.volume["volume_ratio"] <= 0.8:
        alerts.append(
            AlertEvent(
                category="volume",
                rule_type="volume_divergence",
                bias="caution",
                severity="medium",
                title="Volume Divergence",
                detail=f"Price moved {last_move_pct:+.2f}% while volume printed only {analysis.volume['volume_ratio']:.2f}x the recent average.",
            )
        )

    if analysis.volatility["regime"] == "expansion" and current_atr_ratio >= 1.25:
        alerts.append(
            AlertEvent(
                category="volatility",
                rule_type="atr_expansion",
                bias="bullish" if last_move_pct > 0 else "bearish",
                severity="high" if current_atr_ratio >= 1.5 else "medium",
                title="ATR Expansion",
                detail=f"ATR expanded to {current_atr_ratio:.2f}x its recent baseline, indicating increasing range activity.",
            )
        )

    if analysis.volatility["regime"] == "compression" and current_atr_ratio <= 0.85:
        alerts.append(
            AlertEvent(
                category="volatility",
                rule_type="volatility_compression",
                bias="neutral",
                severity="medium",
                title="Volatility Compression",
                detail=f"ATR contracted to {current_atr_ratio:.2f}x its baseline, suggesting a coiling market.",
            )
        )

    if previous_atr_ratio <= 0.9 and current_atr_ratio >= 1.15 and abs(last_move_pct) >= 1.2:
        alerts.append(
            AlertEvent(
                category="volatility",
                rule_type="squeeze_release",
                bias="bullish" if last_move_pct > 0 else "bearish",
                severity="high",
                title="Squeeze Release",
                detail=f"ATR moved from a compressed {previous_atr_ratio:.2f}x baseline to {current_atr_ratio:.2f}x while price moved {last_move_pct:+.2f}%.",
            )
        )

    if previous_ema20 <= previous_ema50 and current_ema20 > current_ema50:
        alerts.append(
            AlertEvent(
                category="trend",
                rule_type="ema20_50_cross",
                bias="bullish",
                severity="high",
                title="EMA20/50 Bullish Cross",
                detail=f"EMA20 crossed above EMA50 at {current_ema20:,.4f} versus {current_ema50:,.4f}.",
            )
        )
    elif previous_ema20 >= previous_ema50 and current_ema20 < current_ema50:
        alerts.append(
            AlertEvent(
                category="trend",
                rule_type="ema20_50_cross",
                bias="bearish",
                severity="high",
                title="EMA20/50 Bearish Cross",
                detail=f"EMA20 crossed below EMA50 at {current_ema20:,.4f} versus {current_ema50:,.4f}.",
            )
        )

    if previous_ema50 <= previous_ema200 and current_ema50 > current_ema200:
        alerts.append(
            AlertEvent(
                category="trend",
                rule_type="ema50_200_cross",
                bias="bullish",
                severity="high",
                title="EMA50/200 Bullish Cross",
                detail=f"EMA50 crossed above EMA200 at {current_ema50:,.4f} versus {current_ema200:,.4f}.",
            )
        )
    elif previous_ema50 >= previous_ema200 and current_ema50 < current_ema200:
        alerts.append(
            AlertEvent(
                category="trend",
                rule_type="ema50_200_cross",
                bias="bearish",
                severity="high",
                title="EMA50/200 Bearish Cross",
                detail=f"EMA50 crossed below EMA200 at {current_ema50:,.4f} versus {current_ema200:,.4f}.",
            )
        )

    if analysis.trend["bias"] != previous_trend["bias"] and abs(analysis.trend["score"] - previous_trend["score"]) >= 15:
        alerts.append(
            AlertEvent(
                category="trend",
                rule_type="trend_reversal",
                bias=str(analysis.trend["bias"]),
                severity="medium" if abs(last_move_pct) < 2 else "high",
                title="Trend Reversal",
                detail=f"Trend regime shifted from {previous_trend['bias']} to {analysis.trend['bias']} with score changing from {previous_trend['score']:.1f} to {analysis.trend['score']:.1f}.",
            )
        )

    if current_rsi >= 70:
        alerts.append(
            AlertEvent(
                category="momentum",
                rule_type="rsi_overbought",
                bias="bearish",
                severity="medium" if current_rsi < 78 else "high",
                title="RSI Overbought",
                detail=f"RSI reached {current_rsi:.2f}, indicating stretched upside momentum.",
            )
        )
    elif current_rsi <= 30:
        alerts.append(
            AlertEvent(
                category="momentum",
                rule_type="rsi_oversold",
                bias="bullish",
                severity="medium" if current_rsi > 22 else "high",
                title="RSI Oversold",
                detail=f"RSI dropped to {current_rsi:.2f}, indicating stretched downside momentum.",
            )
        )

    if previous_macd <= previous_signal and current_macd > current_signal:
        alerts.append(
            AlertEvent(
                category="momentum",
                rule_type="macd_crossover",
                bias="bullish",
                severity="medium",
                title="MACD Bullish Crossover",
                detail=f"MACD crossed above signal with current values {current_macd:.4f} and {current_signal:.4f}.",
            )
        )
    elif previous_macd >= previous_signal and current_macd < current_signal:
        alerts.append(
            AlertEvent(
                category="momentum",
                rule_type="macd_crossover",
                bias="bearish",
                severity="medium",
                title="MACD Bearish Crossover",
                detail=f"MACD crossed below signal with current values {current_macd:.4f} and {current_signal:.4f}.",
            )
        )

    if analysis.momentum["divergence"] in {"bullish", "bearish"}:
        alerts.append(
            AlertEvent(
                category="momentum",
                rule_type="macd_divergence",
                bias=str(analysis.momentum["divergence"]),
                severity="medium",
                title="MACD Divergence",
                detail=f"MACD histogram is showing {analysis.momentum['divergence']} divergence against the recent price move.",
            )
        )

    if analysis.futures.get("available"):
        oi_delta_pct = float(analysis.futures["oi_delta_pct"])
        if abs(oi_delta_pct) >= 5:
            alerts.append(
                AlertEvent(
                    category="futures",
                    rule_type="open_interest_spike",
                    bias=str(analysis.signal["bias"]),
                    severity="high" if abs(oi_delta_pct) >= 10 else "medium",
                    title="Open Interest Spike",
                    detail=f"Open interest changed by {oi_delta_pct:+.2f}% across the latest Bybit sample.",
                )
            )

        current_funding = float(analysis.futures["funding_rate"])
        previous_funding = float(analysis.futures["funding_previous"])
        if _sign(current_funding) != _sign(previous_funding) and abs(current_funding - previous_funding) >= 0.00005:
            alerts.append(
                AlertEvent(
                    category="futures",
                    rule_type="funding_rate_flip",
                    bias="bullish" if current_funding < 0 else "bearish",
                    severity="medium",
                    title="Funding Rate Flip",
                    detail=f"Funding flipped from {previous_funding * 100:+.4f}% to {current_funding * 100:+.4f}%.",
                )
            )

        long_short_ratio = float(analysis.futures["long_short_ratio"])
        if long_short_ratio >= 1.15 or long_short_ratio <= 0.85:
            alerts.append(
                AlertEvent(
                    category="futures",
                    rule_type="long_short_imbalance",
                    bias="bullish" if long_short_ratio > 1 else "bearish",
                    severity="medium" if 0.8 < long_short_ratio < 1.2 else "high",
                    title="Long/Short Imbalance",
                    detail=f"Long/short ratio is at {long_short_ratio:.2f}, indicating a positioning imbalance.",
                )
            )

    bullish_confirmations = len({event.category for event in alerts if event.bias == "bullish"})
    bearish_confirmations = len({event.category for event in alerts if event.bias == "bearish"})

    if analysis.signal["bias"] == "bullish" and bullish_confirmations >= 3:
        alerts.append(
            AlertEvent(
                category="composite",
                rule_type="multi_signal_confirmation",
                bias="bullish",
                severity="high" if bullish_confirmations >= 4 else "medium",
                title="Multi-Signal Confirmation",
                detail=f"Bullish conditions are confirmed across {bullish_confirmations} independent categories with signal confidence at {analysis.signal['confidence']:.1f}/100.",
            )
        )
    elif analysis.signal["bias"] == "bearish" and bearish_confirmations >= 3:
        alerts.append(
            AlertEvent(
                category="composite",
                rule_type="multi_signal_confirmation",
                bias="bearish",
                severity="high" if bearish_confirmations >= 4 else "medium",
                title="Multi-Signal Confirmation",
                detail=f"Bearish conditions are confirmed across {bearish_confirmations} independent categories with signal confidence at {analysis.signal['confidence']:.1f}/100.",
            )
        )

    return alerts


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0

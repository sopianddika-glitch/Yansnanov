from statistics import mean, median


def clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value into a closed interval."""
    return max(low, min(high, value))


def safe_mean(values: list[float]) -> float:
    """Return the arithmetic mean or zero when the input is empty."""
    return mean(values) if values else 0.0


def ema(values: list[float], period: int) -> list[float]:
    """Compute an exponential moving average series."""
    if not values:
        return []

    multiplier = 2 / (period + 1)
    ema_values = [values[0]]

    for value in values[1:]:
        ema_values.append((value - ema_values[-1]) * multiplier + ema_values[-1])

    return ema_values


def rsi(values: list[float], period: int = 14) -> list[float]:
    """Compute Wilder's RSI for a list of closes."""
    if len(values) < 2:
        return [50.0 for _ in values]

    gains = []
    losses = []
    rsis = [50.0]
    avg_gain = 0.0
    avg_loss = 0.0

    for index in range(1, len(values)):
        delta = values[index] - values[index - 1]
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))

        if index < period:
            avg_gain = safe_mean(gains)
            avg_loss = safe_mean(losses)
        elif index == period:
            avg_gain = safe_mean(gains[-period:])
            avg_loss = safe_mean(losses[-period:])
        else:
            avg_gain = ((avg_gain * (period - 1)) + gains[-1]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[-1]) / period

        if avg_loss == 0:
            rs_value = 100.0
        else:
            relative_strength = avg_gain / avg_loss
            rs_value = 100 - (100 / (1 + relative_strength))

        rsis.append(rs_value)

    return rsis


def macd(
    values: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> dict[str, list[float]]:
    """Compute MACD, signal line, and histogram."""
    if not values:
        return {"macd": [], "signal": [], "histogram": []}

    fast_ema = ema(values, fast_period)
    slow_ema = ema(values, slow_period)
    macd_line = [fast_ema[idx] - slow_ema[idx] for idx in range(len(values))]
    signal_line = ema(macd_line, signal_period)
    histogram = [macd_line[idx] - signal_line[idx] for idx in range(len(values))]

    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
    }


def atr(candles: list[dict[str, float]], period: int = 14) -> list[float]:
    """Compute Average True Range from OHLC candles."""
    if not candles:
        return []

    true_ranges = []
    atr_values = []

    for index, candle in enumerate(candles):
        high = candle["high"]
        low = candle["low"]
        if index == 0:
            true_range = high - low
        else:
            previous_close = candles[index - 1]["close"]
            true_range = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )

        true_ranges.append(true_range)

        if index == 0:
            atr_values.append(true_range)
        elif index < period:
            atr_values.append(safe_mean(true_ranges))
        elif index == period:
            atr_values.append(safe_mean(true_ranges[-period:]))
        else:
            atr_values.append(((atr_values[-1] * (period - 1)) + true_range) / period)

    return atr_values


def percent_change(current: float, previous: float) -> float:
    """Return percentage change between two values."""
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


def slope_percent(values: list[float], lookback: int = 10) -> float:
    """Return the percentage slope over a given lookback window."""
    if len(values) < 2:
        return 0.0

    lookback = min(lookback, len(values) - 1)
    start_value = values[-(lookback + 1)]
    end_value = values[-1]
    return percent_change(end_value, start_value)


def detect_histogram_divergence(closes: list[float], histogram: list[float], lookback: int = 8) -> str:
    """Detect a simple bullish or bearish divergence between price and MACD histogram."""
    if len(closes) <= lookback or len(histogram) <= lookback:
        return "none"

    price_delta = closes[-1] - closes[-(lookback + 1)]
    histogram_delta = histogram[-1] - histogram[-(lookback + 1)]

    if price_delta > 0 and histogram_delta < 0:
        return "bearish"
    if price_delta < 0 and histogram_delta > 0:
        return "bullish"
    return "none"


def cluster_levels(levels: list[float], tolerance_pct: float = 0.006) -> list[float]:
    """Cluster nearby levels into cleaner support and resistance zones."""
    clustered: list[list[float]] = []

    for level in sorted(levels):
        bucket = None
        for existing in clustered:
            anchor = safe_mean(existing)
            if anchor == 0:
                continue
            if abs(level - anchor) / anchor <= tolerance_pct:
                bucket = existing
                break

        if bucket is None:
            clustered.append([level])
        else:
            bucket.append(level)

    return [safe_mean(group) for group in clustered]


def find_support_resistance(candles: list[dict[str, float]], pivot_window: int = 3) -> dict[str, list[float]]:
    """Detect support and resistance levels from recent swing highs and lows."""
    if len(candles) < (pivot_window * 2) + 1:
        return {"supports": [], "resistances": []}

    highs = [candle["high"] for candle in candles]
    lows = [candle["low"] for candle in candles]

    support_points = []
    resistance_points = []

    for index in range(pivot_window, len(candles) - pivot_window):
        left_highs = highs[index - pivot_window:index]
        right_highs = highs[index + 1:index + pivot_window + 1]
        left_lows = lows[index - pivot_window:index]
        right_lows = lows[index + 1:index + pivot_window + 1]

        if highs[index] >= max(left_highs + right_highs):
            resistance_points.append(highs[index])
        if lows[index] <= min(left_lows + right_lows):
            support_points.append(lows[index])

    supports = cluster_levels(support_points)
    resistances = cluster_levels(resistance_points)

    return {"supports": supports, "resistances": resistances}


def nearest_levels(current_price: float, supports: list[float], resistances: list[float]) -> dict[str, float | None]:
    """Find the nearest support below and resistance above the current price."""
    nearest_support = max((level for level in supports if level <= current_price), default=None)
    nearest_resistance = min((level for level in resistances if level >= current_price), default=None)

    return {
        "support": nearest_support,
        "resistance": nearest_resistance,
    }


def evaluate_trend(closes: list[float]) -> dict[str, float | str]:
    """Evaluate trend using EMA alignment and slope."""
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    ema200 = ema(closes, 200)

    latest_close = closes[-1]
    latest_ema20 = ema20[-1]
    latest_ema50 = ema50[-1]
    latest_ema200 = ema200[-1]

    score = 50.0
    score += 12 if latest_close > latest_ema20 else -12
    score += 12 if latest_close > latest_ema50 else -12
    score += 12 if latest_close > latest_ema200 else -12
    score += 14 if latest_ema20 > latest_ema50 else -14
    score += 14 if latest_ema50 > latest_ema200 else -14
    score += clamp(slope_percent(ema20, 10) * 2.2, -18, 18)

    score = clamp(score, 0, 100)
    bias = "bullish" if score >= 65 else "bearish" if score <= 35 else "neutral"

    return {
        "ema20": latest_ema20,
        "ema50": latest_ema50,
        "ema200": latest_ema200,
        "score": score,
        "bias": bias,
        "slope_ema20_pct": slope_percent(ema20, 10),
        "slope_ema50_pct": slope_percent(ema50, 20),
    }


def evaluate_momentum(closes: list[float]) -> dict[str, float | str]:
    """Evaluate RSI and MACD momentum."""
    rsi_values = rsi(closes, 14)
    macd_values = macd(closes)

    latest_rsi = rsi_values[-1]
    latest_macd = macd_values["macd"][-1]
    latest_signal = macd_values["signal"][-1]
    latest_histogram = macd_values["histogram"][-1]
    divergence = detect_histogram_divergence(closes, macd_values["histogram"])

    score = 50.0
    score += clamp((latest_rsi - 50) * 0.9, -20, 20)
    score += 15 if latest_macd > latest_signal else -15
    score += 10 if latest_histogram > 0 else -10
    score += 8 if divergence == "bullish" else -8 if divergence == "bearish" else 0
    score = clamp(score, 0, 100)

    bias = "bullish" if score >= 60 else "bearish" if score <= 40 else "neutral"

    return {
        "rsi": latest_rsi,
        "macd": latest_macd,
        "signal": latest_signal,
        "histogram": latest_histogram,
        "divergence": divergence,
        "score": score,
        "bias": bias,
    }


def evaluate_volatility(candles: list[dict[str, float]]) -> dict[str, float | str]:
    """Evaluate ATR and classify volatility regime."""
    atr_values = atr(candles, 14)
    latest_close = candles[-1]["close"]
    latest_atr = atr_values[-1]

    recent_window = atr_values[-21:-1] if len(atr_values) > 20 else atr_values[:-1]
    baseline_atr = median(recent_window) if recent_window else latest_atr
    ratio = latest_atr / baseline_atr if baseline_atr else 1.0
    atr_pct = (latest_atr / latest_close) * 100 if latest_close else 0.0

    if ratio >= 1.25:
        regime = "expansion"
    elif ratio <= 0.85:
        regime = "compression"
    else:
        regime = "balanced"

    return {
        "atr": latest_atr,
        "atr_pct": atr_pct,
        "baseline_atr": baseline_atr,
        "regime": regime,
        "ratio_to_baseline": ratio,
    }


def evaluate_volume(candles: list[dict[str, float]]) -> dict[str, float | str | bool]:
    """Evaluate volume intensity and buyer versus seller pressure."""
    volumes = [candle["volume"] for candle in candles]
    current = candles[-1]
    average_volume = safe_mean(volumes[-21:-1]) if len(volumes) > 20 else safe_mean(volumes[:-1])
    average_volume = average_volume or current["volume"] or 1.0
    ratio = current["volume"] / average_volume

    taker_buy_volume = current.get("taker_buy_base_volume", 0.0)
    buyer_share = (taker_buy_volume / current["volume"]) if current["volume"] else 0.5
    seller_share = 1 - buyer_share
    pressure_score = (buyer_share - seller_share) * 100
    spike = ratio >= 1.5

    if pressure_score >= 10:
        flow_state = "buyers in control"
    elif pressure_score <= -10:
        flow_state = "sellers in control"
    else:
        flow_state = "balanced flow"

    score = clamp(50 + ((ratio - 1) * 18) + (pressure_score * 0.45), 0, 100)

    return {
        "score": score,
        "volume_ratio": ratio,
        "buyer_share": buyer_share * 100,
        "seller_share": seller_share * 100,
        "pressure_score": pressure_score,
        "spike": spike,
        "flow_state": flow_state,
    }


def evaluate_structure(candles: list[dict[str, float]], current_price: float) -> dict[str, float | str | list[float] | None]:
    """Evaluate market structure via swing-based support and resistance levels."""
    levels = find_support_resistance(candles[-140:])
    nearby = nearest_levels(current_price, levels["supports"], levels["resistances"])
    support = nearby["support"]
    resistance = nearby["resistance"]

    support_distance = ((current_price - support) / current_price * 100) if support else None
    resistance_distance = ((resistance - current_price) / current_price * 100) if resistance else None

    if support_distance is not None and support_distance <= 1.0:
        state = "trading near support"
    elif resistance_distance is not None and resistance_distance <= 1.0:
        state = "trading near resistance"
    else:
        state = "inside range"

    return {
        "support_levels": levels["supports"][-3:],
        "resistance_levels": levels["resistances"][:3],
        "nearest_support": support,
        "nearest_resistance": resistance,
        "support_distance_pct": support_distance,
        "resistance_distance_pct": resistance_distance,
        "state": state,
    }


def composite_signal(
    trend: dict[str, float | str],
    momentum: dict[str, float | str],
    volatility: dict[str, float | str],
    volume: dict[str, float | str | bool],
    futures: dict[str, float | str | bool | None],
    price_change_24h: float,
) -> dict[str, float | str]:
    """Blend section-level signals into a directional trading bias."""
    trend_component = float(trend["score"]) - 50
    momentum_component = float(momentum["score"]) - 50
    volume_component = float(volume["score"]) - 50

    futures_component = 0.0
    if futures.get("available"):
        futures_component += clamp(float(futures.get("oi_delta_pct", 0.0)), -12, 12)
        futures_component += clamp(float(futures.get("funding_rate", 0.0)) * 10000, -10, 10)
        futures_component += clamp((float(futures.get("long_short_ratio", 1.0)) - 1.0) * 25, -10, 10)

    score = 50 + (trend_component * 0.40) + (momentum_component * 0.25) + (volume_component * 0.15) + (futures_component * 0.20)
    score += clamp(price_change_24h * 0.3, -8, 8)
    score = clamp(score, 0, 100)

    if score >= 65:
        bias = "bullish"
    elif score <= 35:
        bias = "bearish"
    else:
        bias = "neutral"

    confidence = abs(score - 50) * 2

    if volatility["regime"] == "expansion" and bias != "neutral":
        execution = "trend continuation"
    elif volatility["regime"] == "compression":
        execution = "potential breakout setup"
    else:
        execution = "range to trend transition"

    return {
        "score": score,
        "bias": bias,
        "confidence": confidence,
        "execution": execution,
    }

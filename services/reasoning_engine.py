import logging
from dataclasses import dataclass

from services.ai_service import ai_service
from services.market_engine import MarketAnalysis

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReasoningResult:
    bias: str
    confidence: float
    key_drivers: list[str]
    summary_reasoning: str


class ReasoningEngine:
    """Build natural-language market reasoning from structured analysis."""

    async def reason_about_analysis(
        self,
        analysis: MarketAnalysis,
        user_question: str | None = None,
    ) -> ReasoningResult:
        """Synthesize the analysis into directional reasoning."""
        key_drivers = self._build_key_drivers(analysis)
        summary_reasoning = await self._generate_reasoning_summary(
            analysis,
            key_drivers,
            user_question=user_question,
        )

        return ReasoningResult(
            bias=str(analysis.signal["bias"]),
            confidence=float(analysis.signal["confidence"]),
            key_drivers=key_drivers,
            summary_reasoning=summary_reasoning,
        )

    async def reason_about_scan(
        self,
        analyses: list[MarketAnalysis],
        user_question: str | None = None,
    ) -> str:
        """Generate a portfolio-style overview of a market scan."""
        if not analyses:
            return "No active market setups were detected in the current scan universe."

        bullish = [item for item in analyses if item.signal["bias"] == "bullish"]
        bearish = [item for item in analyses if item.signal["bias"] == "bearish"]
        neutral = [item for item in analyses if item.signal["bias"] == "neutral"]

        strongest = analyses[0]
        weakest = sorted(analyses, key=lambda item: float(item.signal["confidence"]), reverse=True)[-1]

        prompt = (
            "You are a professional crypto market strategist.\n"
            "Write a concise market overview with no bullets and no emojis.\n"
            f"User question: {user_question or 'General market overview'}\n"
            f"Bullish count: {len(bullish)}\n"
            f"Bearish count: {len(bearish)}\n"
            f"Neutral count: {len(neutral)}\n"
            f"Highest conviction setup: {strongest.pair}, bias {strongest.signal['bias']}, confidence {strongest.signal['confidence']:.1f}\n"
            f"Lowest conviction setup: {weakest.pair}, bias {weakest.signal['bias']}, confidence {weakest.signal['confidence']:.1f}\n"
            "Focus on broad market tone, strongest directional pocket, and key risk condition."
        )

        try:
            return await ai_service.generate_response(prompt)
        except RuntimeError as exc:
            logger.warning("AI scan reasoning failed: %s", exc)
            return (
                f"Current market tone is led by {len(bullish)} bullish, {len(bearish)} bearish, and {len(neutral)} neutral setups. "
                f"The strongest configuration is {strongest.pair} with a {strongest.signal['bias']} bias and {strongest.signal['confidence']:.1f}/100 confidence. "
                f"The weakest setup is {weakest.pair}, which reflects lower directional conviction and a more mixed profile."
            )

    def format_reasoning_report(
        self,
        analysis: MarketAnalysis,
        reasoning: ReasoningResult,
    ) -> str:
        """Format reasoning into a Telegram-friendly report."""
        lines = [
            "Natural Language Market Reasoning",
            f"Instrument: {analysis.pair}",
            f"Bias: {reasoning.bias.title()}",
            f"Confidence: {reasoning.confidence:.1f}/100",
            "",
            "Key Drivers",
        ]

        lines.extend(f"- {driver}" for driver in reasoning.key_drivers)
        lines.extend(
            [
                "",
                "Summary",
                reasoning.summary_reasoning,
            ]
        )
        return "\n".join(lines)

    async def _generate_reasoning_summary(
        self,
        analysis: MarketAnalysis,
        key_drivers: list[str],
        user_question: str | None = None,
    ) -> str:
        """Generate a concise narrative explanation of the market state."""
        prompt = (
            "You are a senior quant strategist.\n"
            "Respond in plain professional text with no bullets and no emojis.\n"
            f"User question: {user_question or 'Explain the current market state'}\n"
            f"Instrument: {analysis.pair}\n"
            f"Composite bias: {analysis.signal['bias']}\n"
            f"Composite confidence: {analysis.signal['confidence']:.1f}\n"
            f"Trend score: {analysis.trend['score']:.1f}, bias {analysis.trend['bias']}\n"
            f"Momentum score: {analysis.momentum['score']:.1f}, bias {analysis.momentum['bias']}\n"
            f"Volatility regime: {analysis.volatility['regime']}\n"
            f"Volume flow: {analysis.volume['flow_state']}\n"
            f"Funding bias: {analysis.futures.get('funding_bias', 'unavailable')}\n"
            f"Long short ratio: {analysis.futures.get('long_short_ratio', 'unavailable')}\n"
            f"Key drivers: {'; '.join(key_drivers)}\n"
            "Explain the directional bias, what confirms it, and the main invalidation risk."
        )

        try:
            return await ai_service.generate_response(prompt)
        except RuntimeError as exc:
            logger.warning("AI reasoning summary failed: %s", exc)
            return self._fallback_summary(analysis, key_drivers)

    def _build_key_drivers(self, analysis: MarketAnalysis) -> list[str]:
        """Extract the strongest deterministic drivers from the analysis."""
        drivers = [
            f"Trend score is {analysis.trend['score']:.1f}/100 with {analysis.trend['bias']} EMA alignment",
            f"Momentum score is {analysis.momentum['score']:.1f}/100 and RSI is {analysis.momentum['rsi']:.2f}",
            f"Volatility regime is {analysis.volatility['regime']} with ATR at {analysis.volatility['atr_pct']:.2f}% of price",
            f"Volume flow shows {analysis.volume['flow_state']} at {analysis.volume['volume_ratio']:.2f}x the recent average",
        ]

        if analysis.structure["nearest_support"] is not None:
            drivers.append(f"Nearest support sits near {analysis.structure['nearest_support']:.4f}")
        if analysis.structure["nearest_resistance"] is not None:
            drivers.append(f"Nearest resistance sits near {analysis.structure['nearest_resistance']:.4f}")

        if analysis.futures.get("available"):
            drivers.append(
                f"Futures positioning is {analysis.futures['positioning_bias']} with open interest delta {analysis.futures['oi_delta_pct']:+.2f}%"
            )
            drivers.append(
                f"Funding bias is {analysis.futures['funding_bias']} and long/short ratio is {analysis.futures['long_short_ratio']:.2f}"
            )

        return drivers[:6]

    def _fallback_summary(self, analysis: MarketAnalysis, key_drivers: list[str]) -> str:
        """Produce a deterministic narrative when AI is unavailable."""
        risk = (
            f"Resistance near {analysis.structure['nearest_resistance']:.4f} remains the main invalidation level."
            if analysis.structure["nearest_resistance"] is not None and analysis.signal["bias"] == "bullish"
            else f"Support near {analysis.structure['nearest_support']:.4f} remains the main invalidation level."
            if analysis.structure["nearest_support"] is not None and analysis.signal["bias"] == "bearish"
            else "A shift in trend and momentum alignment would weaken the current thesis."
        )
        return (
            f"{analysis.pair} currently carries a {analysis.signal['bias']} bias with {analysis.signal['confidence']:.1f}/100 confidence. "
            f"The main drivers are {', '.join(key_drivers[:3])}. "
            f"{risk}"
        )


reasoning_engine = ReasoningEngine()

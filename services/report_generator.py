import logging

from services.ai_service import ai_service
from services.market_engine import MarketAnalysis

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Renders analysis objects into Telegram-friendly market reports."""

    async def generate_market_report(self, analysis: MarketAnalysis) -> str:
        """Generate a standard multi-section market report."""
        ai_summary = await self._generate_ai_summary(analysis, mode="market")
        return self._compose_report(analysis, ai_summary=ai_summary, detailed=False)

    async def generate_document_report(self, analysis: MarketAnalysis) -> str:
        """Generate a longer document-style market report."""
        ai_summary = await self._generate_ai_summary(analysis, mode="report")
        return self._compose_report(analysis, ai_summary=ai_summary, detailed=True)

    async def generate_summary_report(self, analysis: MarketAnalysis) -> str:
        """Generate an executive summary report."""
        ai_summary = await self._generate_ai_summary(analysis, mode="summary")

        lines = [
            "Market Intelligence Report",
            f"Instrument: {analysis.pair}",
            f"Signal Bias: {analysis.signal['bias'].title()}",
            f"Signal Confidence: {analysis.signal['confidence']:.1f}/100",
            f"Last Price: {self._format_price(analysis.last_price)}",
            f"24h Change: {analysis.price_change_24h:+.2f}%",
            "",
            "Summary",
            f"Trend Score: {analysis.trend['score']:.1f}/100 ({analysis.trend['bias']})",
            f"Momentum Score: {analysis.momentum['score']:.1f}/100 ({analysis.momentum['bias']})",
            f"Volatility Regime: {analysis.volatility['regime']}",
            f"Volume Flow: {analysis.volume['flow_state']}",
        ]

        if analysis.structure["nearest_support"] is not None:
            lines.append(
                f"Nearest Support: {self._format_price(float(analysis.structure['nearest_support']))}"
            )
        if analysis.structure["nearest_resistance"] is not None:
            lines.append(
                f"Nearest Resistance: {self._format_price(float(analysis.structure['nearest_resistance']))}"
            )

        lines.extend(
            [
                "",
                "AI Summary",
                ai_summary,
            ]
        )

        return "\n".join(lines)

    def generate_signal_report(self, analysis: MarketAnalysis) -> str:
        """Generate a short trading signal view."""
        lines = [
            "Market Intelligence Report",
            f"Instrument: {analysis.pair}",
            "",
            "Signal",
            f"Bias: {analysis.signal['bias'].title()}",
            f"Confidence: {analysis.signal['confidence']:.1f}/100",
            f"Execution Context: {analysis.signal['execution']}",
            f"Trend Score: {analysis.trend['score']:.1f}/100",
            f"Momentum Score: {analysis.momentum['score']:.1f}/100",
            f"Volatility Regime: {analysis.volatility['regime']}",
            f"Buyer/Seller Pressure: {analysis.volume['buyer_share']:.1f}% / {analysis.volume['seller_share']:.1f}%",
        ]

        if analysis.structure["nearest_support"] is not None:
            lines.append(
                f"Nearest Support: {self._format_price(float(analysis.structure['nearest_support']))}"
            )
        if analysis.structure["nearest_resistance"] is not None:
            lines.append(
                f"Nearest Resistance: {self._format_price(float(analysis.structure['nearest_resistance']))}"
            )

        if analysis.futures.get("available"):
            lines.extend(
                [
                    f"Open Interest Delta: {analysis.futures['oi_delta_pct']:+.2f}%",
                    f"Funding Bias: {analysis.futures['funding_bias']}",
                    f"Long/Short Ratio: {analysis.futures['long_short_ratio']:.2f}",
                ]
            )
        else:
            lines.append("Futures Metrics: unavailable")

        return "\n".join(lines)

    def generate_scan_report(self, analyses: list[MarketAnalysis]) -> str:
        """Generate a watchlist-style market scan."""
        lines = [
            "Market Intelligence Scan",
            "Interval: 1h",
            "",
        ]

        for index, analysis in enumerate(analyses, start=1):
            futures_text = (
                f"OI {analysis.futures['oi_delta_pct']:+.2f}% | Funding {analysis.futures['funding_rate'] * 100:+.4f}% | L/S {analysis.futures['long_short_ratio']:.2f}"
                if analysis.futures.get("available")
                else "Futures unavailable"
            )
            lines.append(
                f"{index}. {analysis.pair} | Bias {analysis.signal['bias'].title()} | Confidence {analysis.signal['confidence']:.1f} | 24h {analysis.price_change_24h:+.2f}% | {futures_text}"
            )

        return "\n".join(lines)

    def _compose_report(self, analysis: MarketAnalysis, ai_summary: str, detailed: bool) -> str:
        """Render the full report body."""
        lines = [
            "Market Intelligence Report",
            f"Instrument: {analysis.pair}",
            f"Interval: {analysis.interval}",
            f"Last Price: {self._format_price(analysis.last_price)}",
            f"24h Change: {analysis.price_change_24h:+.2f}%",
            f"24h Range: {self._format_price(analysis.low_price_24h)} - {self._format_price(analysis.high_price_24h)}",
            f"24h Volume: {analysis.volume_24h:,.2f} | Quote Volume: {analysis.quote_volume_24h:,.2f}",
            f"Trade Count: {analysis.trade_count_24h:,}",
            "",
            "Trend",
            f"Trend Bias: {analysis.trend['bias']}",
            f"Trend Strength Score: {analysis.trend['score']:.1f}/100",
            f"EMA20 / EMA50 / EMA200: {self._format_price(float(analysis.trend['ema20']))} / {self._format_price(float(analysis.trend['ema50']))} / {self._format_price(float(analysis.trend['ema200']))}",
            f"EMA20 Slope: {analysis.trend['slope_ema20_pct']:+.2f}% | EMA50 Slope: {analysis.trend['slope_ema50_pct']:+.2f}%",
            f"Market Structure: {analysis.structure['state']}",
            f"Nearest Support: {self._format_optional_price(analysis.structure['nearest_support'])}",
            f"Nearest Resistance: {self._format_optional_price(analysis.structure['nearest_resistance'])}",
            "",
            "Momentum",
            f"Momentum Bias: {analysis.momentum['bias']}",
            f"Momentum Score: {analysis.momentum['score']:.1f}/100",
            f"RSI(14): {analysis.momentum['rsi']:.2f}",
            f"MACD / Signal / Histogram: {analysis.momentum['macd']:.4f} / {analysis.momentum['signal']:.4f} / {analysis.momentum['histogram']:.4f}",
            f"Histogram Divergence: {analysis.momentum['divergence']}",
            "",
            "Volatility",
            f"ATR(14): {analysis.volatility['atr']:.4f}",
            f"ATR % of Price: {analysis.volatility['atr_pct']:.2f}%",
            f"Regime: {analysis.volatility['regime']}",
            f"Expansion Ratio vs Baseline: {analysis.volatility['ratio_to_baseline']:.2f}x",
            "",
            "Volume",
            f"Volume Score: {analysis.volume['score']:.1f}/100",
            f"Current Volume vs 20-Bar Average: {analysis.volume['volume_ratio']:.2f}x",
            f"Buyer Pressure: {analysis.volume['buyer_share']:.1f}%",
            f"Seller Pressure: {analysis.volume['seller_share']:.1f}%",
            f"Flow State: {analysis.volume['flow_state']}",
            "",
            "Futures Metrics",
        ]

        if analysis.futures.get("available"):
            lines.extend(
                [
                    f"Open Interest Delta: {analysis.futures['oi_delta_pct']:+.2f}%",
                    f"Funding Rate: {analysis.futures['funding_rate'] * 100:+.4f}%",
                    f"Funding Bias: {analysis.futures['funding_bias']}",
                    f"Long/Short Ratio: {analysis.futures['long_short_ratio']:.2f}",
                    f"Positioning Bias: {analysis.futures['positioning_bias']}",
                ]
            )
        else:
            lines.append(f"Unavailable: {analysis.futures.get('reason', 'No futures data')}")

        lines.extend(
            [
                "",
                "AI Summary",
                ai_summary,
            ]
        )

        if detailed:
            lines.extend(
                [
                    "",
                    "Execution Framework",
                    f"Composite Bias: {analysis.signal['bias']}",
                    f"Composite Score: {analysis.signal['score']:.1f}/100",
                    f"Confidence: {analysis.signal['confidence']:.1f}/100",
                    f"Preferred Setup: {analysis.signal['execution']}",
                ]
            )

        return "\n".join(lines)

    async def _generate_ai_summary(self, analysis: MarketAnalysis, mode: str) -> str:
        """Generate an AI-assisted summary with a deterministic fallback."""
        prompt = (
            "You are a professional crypto market strategist.\n"
            "Write a concise market intelligence summary with no bullet points and no emojis.\n"
            f"Mode: {mode}\n"
            f"Instrument: {analysis.pair}\n"
            f"Last price: {analysis.last_price}\n"
            f"24h change: {analysis.price_change_24h:+.2f}%\n"
            f"Trend score: {analysis.trend['score']:.1f} ({analysis.trend['bias']})\n"
            f"Momentum score: {analysis.momentum['score']:.1f} ({analysis.momentum['bias']})\n"
            f"RSI: {analysis.momentum['rsi']:.2f}\n"
            f"MACD histogram: {analysis.momentum['histogram']:.4f}\n"
            f"Volatility regime: {analysis.volatility['regime']}\n"
            f"Volume flow: {analysis.volume['flow_state']}\n"
            f"Support: {analysis.structure['nearest_support']}\n"
            f"Resistance: {analysis.structure['nearest_resistance']}\n"
            f"Composite bias: {analysis.signal['bias']}\n"
            f"Composite confidence: {analysis.signal['confidence']:.1f}\n"
            f"Futures available: {analysis.futures.get('available', False)}\n"
            f"Funding bias: {analysis.futures.get('funding_bias', 'unavailable')}\n"
            f"Long short ratio: {analysis.futures.get('long_short_ratio', 'unavailable')}\n"
            "Focus on directional conviction, what confirms the setup, and what would invalidate it."
        )

        try:
            return await ai_service.generate_response(prompt)
        except RuntimeError as exc:
            logger.warning("AI summary generation failed: %s", exc)
            return self._fallback_summary(analysis)

    def _fallback_summary(self, analysis: MarketAnalysis) -> str:
        """Produce a deterministic summary when AI is unavailable."""
        support = self._format_optional_price(analysis.structure["nearest_support"])
        resistance = self._format_optional_price(analysis.structure["nearest_resistance"])

        futures_sentence = (
            f"Bybit futures positioning is {analysis.futures['positioning_bias']} with open interest delta at {analysis.futures['oi_delta_pct']:+.2f}% and funding bias showing {analysis.futures['funding_bias']}."
            if analysis.futures.get("available")
            else "Bybit futures metrics are unavailable, so conviction relies more heavily on spot trend, momentum, volatility, and volume."
        )

        return (
            f"{analysis.pair} is showing a {analysis.signal['bias']} profile with composite confidence at {analysis.signal['confidence']:.1f}/100. "
            f"Trend reads {analysis.trend['bias']} with a trend score of {analysis.trend['score']:.1f}, while momentum is {analysis.momentum['bias']} and RSI is {analysis.momentum['rsi']:.2f}. "
            f"Volatility is currently in {analysis.volatility['regime']} mode and volume flow indicates {analysis.volume['flow_state']}. "
            f"Key structure levels are support at {support} and resistance at {resistance}. "
            f"{futures_sentence}"
        )

    @staticmethod
    def _format_price(value: float) -> str:
        return f"{value:,.4f}".rstrip("0").rstrip(".")

    def _format_optional_price(self, value: float | None) -> str:
        if value is None:
            return "N/A"
        return self._format_price(float(value))


report_generator = ReportGenerator()

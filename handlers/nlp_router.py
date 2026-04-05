import json
import logging
import re
from dataclasses import dataclass

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from services.ai_service import ai_service
from services.alert_engine import alert_engine
from services.market_engine import DEFAULT_SCAN_SYMBOLS, market_engine
from services.market_service import market_service
from services.reasoning_engine import reasoning_engine
from services.report_generator import report_generator

logger = logging.getLogger(__name__)
MAX_MESSAGE_LENGTH = 3900

SYMBOL_ALIASES = {
    "btc": "BTC",
    "bitcoin": "BTC",
    "eth": "ETH",
    "ethereum": "ETH",
    "sol": "SOL",
    "solana": "SOL",
    "bnb": "BNB",
    "xrp": "XRP",
    "ripple": "XRP",
    "cardano": "ADA",
    "doge": "DOGE",
    "dogecoin": "DOGE",
    "link": "LINK",
    "chainlink": "LINK",
    "sui": "SUI",
    "avax": "AVAX",
    "arbitrum": "ARB",
    "arb": "ARB",
}

ALERT_TYPE_ALIASES = {
    "breakout": "breakout",
    "break down": "breakdown",
    "breakdown": "breakdown",
    "sudden move": "sudden_move",
    "deviation": "deviation",
    "volume spike": "volume_spike",
    "volume divergence": "volume_divergence",
    "atr expansion": "atr_expansion",
    "volatility compression": "volatility_compression",
    "compression": "volatility_compression",
    "squeeze release": "squeeze_release",
    "ema20 50 cross": "ema20_50_cross",
    "ema20/50": "ema20_50_cross",
    "ema50 200 cross": "ema50_200_cross",
    "ema50/200": "ema50_200_cross",
    "trend reversal": "trend_reversal",
    "rsi overbought": "rsi_overbought",
    "rsi oversold": "rsi_oversold",
    "macd crossover": "macd_crossover",
    "macd cross": "macd_crossover",
    "macd divergence": "macd_divergence",
    "oi spike": "open_interest_spike",
    "open interest spike": "open_interest_spike",
    "funding flip": "funding_rate_flip",
    "funding rate flip": "funding_rate_flip",
    "long short imbalance": "long_short_imbalance",
    "long/short imbalance": "long_short_imbalance",
    "multi signal": "multi_signal_confirmation",
    "multi-signal": "multi_signal_confirmation",
}

INTENT_KEYWORDS = {
    "price_check": [
        ("harga", 3),
        ("price", 3),
        ("berapa", 2),
        ("cek", 2),
        ("cekin", 2),
        ("lihat", 1),
    ],
    "market_report": [
        ("buat laporan", 5),
        ("laporan", 4),
        ("full report", 4),
        ("dokumen", 3),
        ("report", 3),
    ],
    "market_summary": [
        ("market hari ini", 5),
        ("gimana", 3),
        ("bagaimana", 3),
        ("ringkasan", 3),
        ("summary", 3),
        ("analisa", 2),
        ("jelasin", 2),
        ("overview", 2),
    ],
    "signal": [
        ("signal", 4),
        ("sinyal", 4),
        ("setup", 2),
        ("bias", 2),
        ("entry", 2),
    ],
    "market_scan": [
        ("scan market", 5),
        ("market scan", 5),
        ("scan", 2),
        ("watchlist", 2),
    ],
    "alert_set": [
        ("kasih alert", 5),
        ("set alert", 5),
        ("pasang alert", 5),
        ("buat alert", 5),
        ("alertin", 4),
    ],
    "alert_report": [
        ("alert", 2),
        ("peringatan", 2),
        ("warning", 2),
    ],
    "alert_scan": [
        ("potensi breakout", 5),
        ("potensi breakdown", 5),
        ("funding flip", 4),
        ("breakout ga", 4),
        ("breakdown ga", 4),
        ("cari breakout", 4),
        ("scan alert", 4),
    ],
}


@dataclass(slots=True)
class NLPRoute:
    intent: str
    symbol: str | None
    alert_type: str | None
    confidence: float
    raw_text: str


class NaturalLanguageRouter:
    """Detect intent from free text and route to the right market engine."""

    async def classify_message(self, text: str) -> NLPRoute:
        normalized = self._normalize_text(text)
        symbol = self.extract_symbol(text, normalized)
        alert_type = self.extract_alert_type(normalized)
        scores = self._score_intents(normalized, symbol=symbol, alert_type=alert_type)

        top_intent, top_score = max(scores.items(), key=lambda item: item[1])
        sorted_scores = sorted(scores.values(), reverse=True)
        confidence = min(0.98, 0.35 + (top_score * 0.08))

        if top_score <= 2 or (len(sorted_scores) > 1 and abs(sorted_scores[0] - sorted_scores[1]) <= 1):
            ai_route = await self._ai_semantic_route(normalized, symbol, alert_type)
            if ai_route is not None:
                return ai_route
            if top_score == 0:
                return NLPRoute(
                    intent="unknown",
                    symbol=symbol,
                    alert_type=alert_type,
                    confidence=0.1,
                    raw_text=text,
                )

        if alert_type and "alert" in top_intent and top_intent != "alert_set":
            top_intent = "alert_scan" if symbol is None else "alert_report"

        if symbol and top_intent == "price_check" and any(token in normalized for token in ("laporan", "report", "summary", "gimana", "analisa", "signal")):
            top_intent = "market_summary"

        if symbol and top_intent == "market_scan":
            top_intent = "market_summary"

        return NLPRoute(
            intent=top_intent,
            symbol=symbol,
            alert_type=alert_type,
            confidence=confidence,
            raw_text=text,
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle non-command text messages as natural language market requests."""
        if update.effective_message is None or not update.effective_message.text:
            return

        route = await self.classify_message(update.effective_message.text)
        await self._send_typing(update, context)

        try:
            response = await self._execute_route(route, update, context)
        except Exception as exc:
            logger.exception("Natural language routing failed for '%s'", route.raw_text)
            await update.effective_message.reply_text(
                f"I couldn't process that market request cleanly: {exc}"
            )
            return

        if response:
            await self._send_chunked_text(update, response)

    async def _execute_route(
        self,
        route: NLPRoute,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> str:
        """Route a classified natural-language request to the appropriate engine."""
        if route.intent == "market_report":
            if route.symbol is None:
                return "Specify an instrument for the report, for example: buat laporan BTC"
            analysis = await market_engine.analyze_symbol(route.symbol)
            return await report_generator.generate_document_report(analysis)

        if route.intent == "market_summary":
            if route.symbol is None:
                analyses = await market_engine.scan_market()
                reasoning = await reasoning_engine.reason_about_scan(analyses, route.raw_text)
                top_setups = analyses[:3]
                lines = [
                    "Natural Language Market Overview",
                    f"Market Breadth: {len(analyses)} instruments scanned",
                    "",
                    "Top Setups",
                ]
                lines.extend(
                    f"- {item.pair}: bias {item.signal['bias']}, confidence {item.signal['confidence']:.1f}/100, 24h {item.price_change_24h:+.2f}%"
                    for item in top_setups
                )
                lines.extend(["", "Summary", reasoning])
                return "\n".join(lines)

            analysis = await market_engine.analyze_symbol(route.symbol)
            reasoning = await reasoning_engine.reason_about_analysis(analysis, route.raw_text)
            return reasoning_engine.format_reasoning_report(analysis, reasoning)

        if route.intent == "signal":
            if route.symbol is None:
                return "Specify an instrument for the signal view, for example: signal BTC"
            analysis = await market_engine.analyze_symbol(route.symbol)
            return report_generator.generate_signal_report(analysis)

        if route.intent == "market_scan":
            analyses = await market_engine.scan_market(
                symbols=[route.symbol] if route.symbol else None
            )
            if not analyses:
                return "No scan results are available right now."
            scan_report = report_generator.generate_scan_report(analyses)
            scan_reasoning = await reasoning_engine.reason_about_scan(analyses, route.raw_text)
            return f"{scan_report}\n\nSummary\n{scan_reasoning}"

        if route.intent == "alert_set":
            if route.alert_type is None:
                return (
                    "Specify the alert condition you want to track, for example: "
                    "kasih alert BTC funding flip"
                )
            if route.symbol is None:
                filtered_scan = await self._build_filtered_alert_scan(alert_type=route.alert_type)
                return (
                    filtered_scan
                    + "\n\nTo register a persistent alert, include a symbol. Example: kasih alert BTC funding flip"
                )

            subscription = alert_engine.set_alert_subscription(
                context.application.bot_data,
                update.effective_chat.id if update.effective_chat else 0,
                route.symbol,
                route.alert_type,
            )
            return (
                "Alert subscription saved.\n"
                f"Instrument: {subscription['symbol']}USDT\n"
                f"Active filters: {', '.join(subscription['types'])}"
            )

        if route.intent == "alert_report":
            if route.symbol is None:
                if route.alert_type is not None:
                    return await self._build_filtered_alert_scan(alert_type=route.alert_type)
                return "Specify an instrument for alert review, for example: alert BTC"
            return await alert_engine.build_manual_alert_report(route.symbol)

        if route.intent == "alert_scan":
            return await self._build_filtered_alert_scan(
                alert_type=route.alert_type,
                symbols=[route.symbol] if route.symbol else None,
            )

        if route.intent == "price_check":
            if route.symbol is None:
                return "Specify an instrument to check, for example: cek BTC"
            pair, price = await market_service.get_price(route.symbol)
            analysis = await market_engine.analyze_symbol(route.symbol)
            return (
                "Market Price Check\n"
                f"Instrument: {pair}\n"
                f"Last Price: {price:,.4f}".rstrip("0").rstrip(".")
                + "\n"
                + f"24h Change: {analysis.price_change_24h:+.2f}%\n"
                + f"Signal Bias: {analysis.signal['bias'].title()} ({analysis.signal['confidence']:.1f}/100)"
            )

        if route.intent == "unknown":
            return (
                "I can help with market, alert, scan, report, and price requests.\n"
                "Examples:\n"
                "cek BTC\n"
                "buat laporan BTC\n"
                "scan market\n"
                "kasih alert BTC funding flip"
            )

        if route.symbol:
            analysis = await market_engine.analyze_symbol(route.symbol)
            reasoning = await reasoning_engine.reason_about_analysis(analysis, route.raw_text)
            return reasoning_engine.format_reasoning_report(analysis, reasoning)

        analyses = await market_engine.scan_market()
        reasoning = await reasoning_engine.reason_about_scan(analyses, route.raw_text)
        return f"Natural Language Market Overview\n\n{reasoning}"

    async def _build_filtered_alert_scan(
        self,
        alert_type: str | None,
        symbols: list[str] | None = None,
    ) -> str:
        """Build an alert scan and filter it to one alert type when requested."""
        results = await alert_engine.scan_symbols(symbols=symbols)
        if not results:
            return "No triggered alerts were detected across the current scan universe."

        if alert_type is None:
            return alert_engine.format_scan_report(results)

        filtered_results = {}
        for symbol, (analysis, alerts) in results.items():
            matched = alert_engine.filter_alerts(alerts, {alert_type})
            if matched:
                filtered_results[symbol] = (analysis, matched)

        if not filtered_results:
            return f"No active {alert_type} alerts were detected in the current scan universe."

        return alert_engine.format_scan_report(filtered_results)

    def extract_symbol(self, raw_text: str, normalized_text: str) -> str | None:
        """Extract a market symbol from natural language."""
        valid_symbols = {value for value in SYMBOL_ALIASES.values()}

        for token in re.findall(r"[A-Za-z0-9/]+", raw_text):
            cleaned = token.replace("/", "")
            upper = cleaned.upper()
            if upper.endswith("USDT") and len(upper) > 4:
                return upper[:-4]
            if 2 <= len(upper) <= 6 and cleaned.isalpha() and cleaned == upper and upper in valid_symbols:
                return upper

        for token in re.findall(r"[a-zA-Z0-9/]+", normalized_text):
            cleaned = token.lower().replace("/", "")
            if cleaned in SYMBOL_ALIASES:
                return SYMBOL_ALIASES[cleaned]

        return None

    def extract_alert_type(self, normalized_text: str) -> str | None:
        """Extract a known alert type phrase from natural language."""
        for phrase, alert_type in sorted(ALERT_TYPE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if phrase in normalized_text:
                return alert_type
        return None

    def _score_intents(
        self,
        normalized_text: str,
        symbol: str | None,
        alert_type: str | None,
    ) -> dict[str, int]:
        """Score intents using weighted keyword and phrase matches."""
        scores = {intent: 0 for intent in INTENT_KEYWORDS}

        for intent, phrases in INTENT_KEYWORDS.items():
            for phrase, weight in phrases:
                if phrase in normalized_text:
                    scores[intent] += weight

        if symbol is not None:
            scores["price_check"] += 1
            scores["market_summary"] += 1
            scores["market_report"] += 1 if "laporan" in normalized_text or "report" in normalized_text else 0
            scores["signal"] += 1 if "signal" in normalized_text or "setup" in normalized_text else 0

        if alert_type is not None:
            scores["alert_set"] += 2
            scores["alert_report"] += 2
            scores["alert_scan"] += 3 if symbol is None else 1

        if normalized_text.startswith("cek ") and symbol is not None:
            scores["price_check"] += 3

        if "potensi" in normalized_text and ("breakout" in normalized_text or "breakdown" in normalized_text):
            scores["alert_scan"] += 4

        if "buat laporan" in normalized_text and symbol is not None:
            scores["market_report"] += 4

        if "scan market" in normalized_text or normalized_text.strip() == "scan":
            scores["market_scan"] += 5

        return scores

    async def _ai_semantic_route(
        self,
        normalized_text: str,
        symbol: str | None,
        alert_type: str | None,
    ) -> NLPRoute | None:
        """Use AI as a semantic fallback when keyword routing is ambiguous."""
        prompt = (
            "Classify the user message into one of these intents only: "
            "price_check, market_report, market_summary, signal, market_scan, alert_set, alert_report, alert_scan.\n"
            "Return strict JSON with keys intent, symbol, alert_type, confidence.\n"
            "Use null for unknown symbol or alert_type.\n"
            f"Detected symbol candidate: {symbol}\n"
            f"Detected alert candidate: {alert_type}\n"
            f"User message: {normalized_text}"
        )

        try:
            response = await ai_service.generate_response(prompt)
        except RuntimeError as exc:
            logger.warning("AI semantic router unavailable: %s", exc)
            return None

        payload = self._extract_json(response)
        if payload is None:
            return None

        try:
            intent = str(payload["intent"])
            ai_symbol = payload.get("symbol") or symbol
            ai_alert_type = payload.get("alert_type") or alert_type
            confidence = float(payload.get("confidence", 0.55))
        except (KeyError, TypeError, ValueError):
            return None

        return NLPRoute(
            intent=intent,
            symbol=str(ai_symbol).upper() if ai_symbol else None,
            alert_type=str(ai_alert_type) if ai_alert_type else None,
            confidence=max(0.4, min(confidence, 0.99)),
            raw_text=normalized_text,
        )

    @staticmethod
    def _extract_json(text: str) -> dict | None:
        """Extract a JSON object from a text response."""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for matching."""
        lowered = text.lower().strip()
        lowered = lowered.replace("?", " ").replace("!", " ").replace(",", " ")
        return re.sub(r"\s+", " ", lowered)

    async def _send_typing(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a typing indicator while processing natural language."""
        if update.effective_chat is None:
            return

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

    async def _send_chunked_text(self, update: Update, text: str) -> None:
        """Send large responses in Telegram-safe chunks."""
        if update.effective_message is None:
            return

        for chunk in self._chunk_text(text):
            await update.effective_message.reply_text(chunk)

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = MAX_MESSAGE_LENGTH) -> list[str]:
        """Split long responses into smaller messages."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if end < len(text):
                split_at = chunk.rfind("\n")
                if split_at > chunk_size // 2:
                    end = start + split_at
                    chunk = text[start:end]
            chunks.append(chunk.strip())
            start = end
        return [chunk for chunk in chunks if chunk]


nlp_router = NaturalLanguageRouter()


async def natural_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for non-command natural-language requests."""
    await nlp_router.handle_message(update, context)

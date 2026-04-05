import logging
import time
from collections import defaultdict

from telegram.ext import Application

from services.alert_rules import ALERT_CATEGORIES, ALERT_RULE_TYPES, AlertEvent, evaluate_alerts
from services.market_engine import DEFAULT_SCAN_SYMBOLS, MarketAnalysis, market_engine

logger = logging.getLogger(__name__)
ALERT_COOLDOWN_SECONDS = 60 * 60


class AlertEngine:
    """Coordinates alert evaluation, formatting, and subscription handling."""

    def initialize_state(self, bot_data: dict) -> None:
        """Ensure in-memory alert storage exists."""
        bot_data.setdefault("alert_subscriptions", {})
        bot_data.setdefault("alert_delivery_cache", {})

    async def analyze_symbol(self, symbol: str, interval: str = "1h") -> tuple[MarketAnalysis, list[AlertEvent]]:
        """Build a market analysis snapshot and evaluate active alerts."""
        analysis = await market_engine.analyze_symbol(symbol, interval=interval)
        alerts = evaluate_alerts(analysis)
        return analysis, alerts

    async def scan_symbols(
        self,
        symbols: list[str] | None = None,
        interval: str = "1h",
    ) -> dict[str, tuple[MarketAnalysis, list[AlertEvent]]]:
        """Scan a list of symbols and return only triggered alerts."""
        scan_list = symbols or list(DEFAULT_SCAN_SYMBOLS)
        results: dict[str, tuple[MarketAnalysis, list[AlertEvent]]] = {}

        for symbol in scan_list:
            try:
                analysis, alerts = await self.analyze_symbol(symbol, interval=interval)
            except Exception as exc:
                logger.warning("Alert scan skipped %s: %s", symbol, exc)
                continue

            if alerts:
                results[analysis.symbol] = (analysis, alerts)

        return results

    def set_alert_subscription(self, bot_data: dict, chat_id: int, symbol: str, alert_type: str) -> dict:
        """Register a symbol and alert type for a chat."""
        self.initialize_state(bot_data)
        normalized_symbol = self.normalize_symbol(symbol)
        normalized_type = self.normalize_alert_type(alert_type)

        subscriptions = bot_data["alert_subscriptions"]
        chat_subscriptions = subscriptions.setdefault(chat_id, {})
        alert_types = chat_subscriptions.setdefault(normalized_symbol, set())

        if normalized_type == "all":
            alert_types.clear()
            alert_types.add("all")
        else:
            if "all" in alert_types:
                alert_types.remove("all")
            alert_types.add(normalized_type)

        return {
            "symbol": normalized_symbol,
            "types": sorted(alert_types),
        }

    def get_chat_subscriptions(self, bot_data: dict, chat_id: int) -> dict[str, set[str]]:
        """Return stored subscriptions for one chat."""
        self.initialize_state(bot_data)
        return bot_data["alert_subscriptions"].get(chat_id, {})

    async def build_manual_alert_report(self, symbol: str) -> str:
        """Build a full alert report for one symbol."""
        analysis, alerts = await self.analyze_symbol(symbol)
        return self.format_alert_report(analysis, alerts)

    async def build_scan_report(self, symbols: list[str] | None = None) -> str:
        """Build an aggregate alert scan report."""
        results = await self.scan_symbols(symbols=symbols)
        return self.format_scan_report(results)

    async def collect_scheduled_deliveries(self, application: Application) -> list[tuple[int, str]]:
        """Scan configured alerts and return messages that should be delivered."""
        self.initialize_state(application.bot_data)
        subscriptions = application.bot_data["alert_subscriptions"]
        if not subscriptions:
            return []

        unique_symbols = sorted({symbol for chat_map in subscriptions.values() for symbol in chat_map})
        if not unique_symbols:
            return []

        results = await self.scan_symbols(symbols=unique_symbols)
        if not results:
            return []

        deliveries: list[tuple[int, str]] = []
        grouped_reports: dict[int, list[str]] = defaultdict(list)

        for chat_id, symbol_map in subscriptions.items():
            for symbol, alert_filters in symbol_map.items():
                if symbol not in results:
                    continue

                analysis, alerts = results[symbol]
                matched = self.filter_alerts(alerts, alert_filters)
                matched = [event for event in matched if self._mark_if_deliverable(application.bot_data, chat_id, symbol, event)]
                if not matched:
                    continue

                grouped_reports[chat_id].append(
                    self.format_alert_report(
                        analysis,
                        matched,
                        heading="Automated Market Alert",
                    )
                )

        for chat_id, sections in grouped_reports.items():
            deliveries.append((chat_id, "\n\n".join(sections)))

        return deliveries

    def filter_alerts(self, alerts: list[AlertEvent], alert_filters: set[str]) -> list[AlertEvent]:
        """Filter alerts by configured rule type or category."""
        if not alert_filters or "all" in alert_filters:
            return alerts

        return [
            event
            for event in alerts
            if event.rule_type in alert_filters or event.category in alert_filters
        ]

    def format_alert_report(
        self,
        analysis: MarketAnalysis,
        alerts: list[AlertEvent],
        heading: str = "Advanced Alert Report",
    ) -> str:
        """Format one symbol's alert output."""
        lines = [
            heading,
            f"Instrument: {analysis.pair}",
            f"Last Price: {analysis.last_price:,.4f}".rstrip("0").rstrip("."),
            f"Signal Bias: {analysis.signal['bias']}",
            f"Signal Confidence: {analysis.signal['confidence']:.1f}/100",
            f"Triggered Alerts: {len(alerts)}",
            "",
        ]

        if not alerts:
            lines.extend(
                [
                    "Status",
                    "No active alerts are currently triggered for this instrument.",
                ]
            )
            return "\n".join(lines)

        for index, event in enumerate(alerts, start=1):
            lines.extend(
                [
                    f"{index}. {event.title}",
                    f"Category: {event.category}",
                    f"Type: {event.rule_type}",
                    f"Bias: {event.bias}",
                    f"Severity: {event.severity}",
                    f"Detail: {event.detail}",
                    "",
                ]
            )

        return "\n".join(lines).strip()

    def format_scan_report(self, results: dict[str, tuple[MarketAnalysis, list[AlertEvent]]]) -> str:
        """Format a cross-market alert scan."""
        lines = [
            "Advanced Alert Scan",
            f"Triggered Markets: {len(results)}",
            "",
        ]

        if not results:
            lines.append("No triggered alerts were detected across the current scan universe.")
            return "\n".join(lines)

        for symbol, (analysis, alerts) in results.items():
            highest_severity = self._highest_severity(alerts)
            alert_names = ", ".join(event.rule_type for event in alerts[:4])
            lines.append(
                f"{analysis.pair} | Alerts {len(alerts)} | Highest Severity {highest_severity} | Bias {analysis.signal['bias']} | Confidence {analysis.signal['confidence']:.1f} | Active Rules {alert_names}"
            )

        return "\n".join(lines)

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper().replace("/", "").replace("-", "")
        if normalized.endswith("USDT"):
            normalized = normalized[:-4]
        if not normalized:
            raise ValueError("Please provide a valid symbol.")
        return normalized

    @staticmethod
    def normalize_alert_type(alert_type: str) -> str:
        normalized = alert_type.strip().lower().replace("-", "_")
        if normalized not in ALERT_CATEGORIES | ALERT_RULE_TYPES | {"all"}:
            allowed = ", ".join(sorted(ALERT_CATEGORIES | ALERT_RULE_TYPES | {"all"}))
            raise ValueError(f"Unknown alert type '{alert_type}'. Allowed values: {allowed}")
        return normalized

    def _mark_if_deliverable(self, bot_data: dict, chat_id: int, symbol: str, event: AlertEvent) -> bool:
        """Rate-limit scheduler deliveries for repeated alerts."""
        cache = bot_data["alert_delivery_cache"]
        cache_key = f"{chat_id}:{symbol}:{event.signature}"
        now = time.time()
        last_sent = cache.get(cache_key, 0)
        if now - last_sent < ALERT_COOLDOWN_SECONDS:
            return False

        cache[cache_key] = now
        return True

    @staticmethod
    def _highest_severity(alerts: list[AlertEvent]) -> str:
        order = {"medium": 1, "high": 2, "critical": 3}
        best = max(alerts, key=lambda item: order.get(item.severity, 0))
        return best.severity


alert_engine = AlertEngine()

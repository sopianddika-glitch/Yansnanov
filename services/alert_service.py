from services.alert_rules import ALERT_CATEGORIES, ALERT_RULE_TYPES
from services.alert_engine import alert_engine
from utils.logger import get_logger

logger = get_logger(__name__)


class AlertService:
    """Alert registry and scan interface for Telegram handlers."""

    def __init__(self) -> None:
        self._registry: dict[int, dict[str, set[str]]] = {}

    def register_alert(self, user_id: int, symbol: str, alert_type: str) -> dict:
        """Register a symbol + alert type for a user."""
        normalized_type = self.normalize_alert_type(alert_type)
        normalized_symbol = alert_engine.normalize_symbol(symbol)

        user_alerts = self._registry.setdefault(user_id, {})
        symbol_alerts = user_alerts.setdefault(normalized_symbol, set())

        if normalized_type == "all":
            symbol_alerts.clear()
            symbol_alerts.add("all")
        else:
            if "all" in symbol_alerts:
                symbol_alerts.remove("all")
            symbol_alerts.add(normalized_type)

        return {
            "user_id": user_id,
            "symbol": normalized_symbol,
            "types": sorted(symbol_alerts),
        }

    async def scan_alerts(self) -> list[str]:
        """Scan all registered alerts and return text-ready triggered messages."""
        watched_symbols = sorted({symbol for user_alerts in self._registry.values() for symbol in user_alerts})
        results = await alert_engine.scan_symbols(symbols=watched_symbols or None)
        messages = []

        for user_id, symbol_map in self._registry.items():
            for symbol, alert_filters in symbol_map.items():
                if symbol not in results:
                    continue

                analysis, alerts = results[symbol]
                matched = alert_engine.filter_alerts(alerts, alert_filters)
                if matched:
                    messages.append(
                        alert_engine.format_alert_report(
                            analysis,
                            matched,
                            heading=f"Alert Feed for User {user_id}",
                        )
                    )

        return messages

    async def build_alert_report(self, symbol: str) -> str:
        """Build a one-off alert report for one symbol."""
        return await alert_engine.build_manual_alert_report(symbol)

    async def build_scan_report(self, symbols: list[str] | None = None) -> str:
        """Build an aggregate alert scan report."""
        return await alert_engine.build_scan_report(symbols=symbols)

    @staticmethod
    def normalize_alert_type(alert_type: str) -> str:
        normalized = alert_type.strip().lower().replace("-", "_")
        if normalized not in ALERT_CATEGORIES | ALERT_RULE_TYPES | {"all"}:
            allowed = ", ".join(sorted(ALERT_CATEGORIES | ALERT_RULE_TYPES | {"all"}))
            raise ValueError(f"Unknown alert type '{alert_type}'. Allowed values: {allowed}")
        return normalized

    def get_registry(self) -> dict[int, dict[str, set[str]]]:
        """Expose registered alerts for debugging or admin use."""
        return self._registry


alert_service = AlertService()

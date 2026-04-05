from services.market_service import DEFAULT_SCAN_SYMBOLS, market_service


class AlertService:
    VALID_TYPES = {"breakout", "breakdown", "sudden_move", "deviation", "all"}

    def __init__(self) -> None:
        self._registry: dict[int, dict[str, set[str]]] = {}

    def register_alert(self, user_id: int, symbol: str, alert_type: str) -> dict:
        normalized_symbol = symbol.strip().upper().replace("USDT", "")
        normalized_type = alert_type.strip().lower()
        if normalized_type not in self.VALID_TYPES:
            raise ValueError(
                "Unsupported alert type. Use breakout, breakdown, sudden_move, deviation, or all."
            )
        types = (
            {"breakout", "breakdown", "sudden_move", "deviation"}
            if normalized_type == "all"
            else {normalized_type}
        )
        user_alerts = self._registry.setdefault(user_id, {})
        existing = user_alerts.setdefault(normalized_symbol, set())
        existing.update(types)
        return {"user_id": user_id, "symbol": normalized_symbol, "types": sorted(existing)}

    async def build_alert_report(self, symbol: str) -> str:
        snapshot = await market_service.get_market_snapshot(symbol)
        matches = self._evaluate_snapshot(snapshot)
        if not matches:
            return (
                "Alert Report\n"
                f"Instrument: {snapshot['pair']}\n"
                "No active alert conditions are currently triggered."
            )
        lines = ["Alert Report", f"Instrument: {snapshot['pair']}"]
        lines.extend(f"- {match}" for match in matches)
        return "\n".join(lines)

    async def scan_alerts(self) -> list[str]:
        messages: list[str] = []
        for user_id, symbol_map in self._registry.items():
            for symbol, types in symbol_map.items():
                snapshot = await market_service.get_market_snapshot(symbol)
                matches = self._evaluate_snapshot(snapshot, filters=types)
                if matches:
                    messages.append(f"User {user_id} | {snapshot['pair']} | {'; '.join(matches)}")
        return messages

    async def scan_watchlist(self, symbols: tuple[str, ...] | None = None) -> str:
        snapshots = await market_service.scan_market(symbols or DEFAULT_SCAN_SYMBOLS)
        lines = ["Alert Scan"]
        for snapshot in snapshots:
            matches = self._evaluate_snapshot(snapshot)
            if matches:
                lines.append(f"- {snapshot['pair']}: {'; '.join(matches)}")
        if len(lines) == 1:
            lines.append("No triggered alert conditions were found in the watchlist.")
        return "\n".join(lines)

    @staticmethod
    def _evaluate_snapshot(snapshot: dict, filters: set[str] | None = None) -> list[str]:
        active = filters or {"breakout", "breakdown", "sudden_move", "deviation"}
        signals: list[str] = []
        if "breakout" in active and snapshot["price"] >= snapshot["high_price"] * 0.997:
            signals.append("breakout condition is active near the 24h high")
        if "breakdown" in active and snapshot["price"] <= snapshot["low_price"] * 1.003:
            signals.append("breakdown condition is active near the 24h low")
        if "sudden_move" in active and abs(snapshot["change_percent"]) >= 3.0:
            signals.append(f"sudden_move detected with {snapshot['change_percent']:+.2f}% 24h change")
        if "deviation" in active and abs(snapshot["deviation_percent"]) >= 2.0:
            signals.append(
                f"deviation detected at {snapshot['deviation_percent']:+.2f}% versus weighted average"
            )
        return signals


alert_service = AlertService()

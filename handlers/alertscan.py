from telegram import Update
from telegram.ext import ContextTypes

from services.alert_service import alert_service


async def alertscan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    triggered = await alert_service.scan_alerts()
    watchlist_text = await alert_service.scan_watchlist()
    if not triggered:
        await update.effective_message.reply_text(
            watchlist_text + "\n\nRegistered Alerts\nNo registered alerts are currently triggered."
        )
        return
    lines = [watchlist_text, "", "Registered Alerts"]
    lines.extend(f"- {item}" for item in triggered)
    await update.effective_message.reply_text("\n".join(lines))

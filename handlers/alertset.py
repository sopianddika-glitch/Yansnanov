from telegram import Update
from telegram.ext import ContextTypes

from services.alert_service import alert_service


async def alertset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.effective_message.reply_text(
            "Usage: /alertset <symbol> <type>"
        )
        return
    symbol = context.args[0].strip()
    alert_type = context.args[1].strip().lower()
    try:
        subscription = alert_service.register_alert(
            user_id=update.effective_user.id if update.effective_user else 0,
            symbol=symbol,
            alert_type=alert_type,
        )
    except ValueError as exc:
        await update.effective_message.reply_text(str(exc))
        return
    await update.effective_message.reply_text(
        "Alert registered\n"
        f"Instrument: {subscription['symbol']}USDT\n"
        f"Active Types: {', '.join(subscription['types'])}"
    )

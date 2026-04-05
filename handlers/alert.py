from telegram import Update
from telegram.ext import ContextTypes

from services.alert_service import alert_service


async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    symbol = _symbol_from_args(context.args)
    if not symbol:
        await update.effective_message.reply_text("Usage: /alert <symbol>")
        return
    report = await alert_service.build_alert_report(symbol)
    await update.effective_message.reply_text(report)


def _symbol_from_args(args: list[str]) -> str | None:
    return args[0].strip() if args else None

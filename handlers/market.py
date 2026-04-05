from telegram import Update
from telegram.ext import ContextTypes

from services.market_service import market_service


async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    symbol = _symbol_from_args(context.args)
    if not symbol:
        await update.effective_message.reply_text("Usage: /market <symbol>")
        return
    snapshot = await market_service.get_market_snapshot(symbol)
    await update.effective_message.reply_text(market_service.format_market_text(snapshot))


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    snapshots = await market_service.scan_market()
    await update.effective_message.reply_text(market_service.format_scan_text(snapshots))


def _symbol_from_args(args: list[str]) -> str | None:
    return args[0].strip() if args else None

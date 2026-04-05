from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from services.hybrid_service import hybrid_service
from services.report_service import report_service
from utils.formatting import chunk_text
from utils.logger import get_logger

logger = get_logger(__name__)


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return the hybrid spot price view."""
    if update.effective_message is None:
        return
    if not context.args:
        await update.effective_message.reply_text("Usage: /price <symbol>")
        return

    await _send_typing(update, context)
    try:
        hybrid_price = await hybrid_service.get_hybrid_price(context.args[0])
    except Exception as exc:
        await update.effective_message.reply_text(str(exc))
        return

    spread = hybrid_price["spread_info"]
    response = (
        "Hybrid Price Snapshot\n"
        f"Instrument: {hybrid_price['symbol']}USDT\n"
        f"Primary Exchange: {hybrid_price['exchange_primary']}\n"
        f"Secondary Exchange: {hybrid_price['exchange_secondary']}\n"
        f"Primary Price: {spread['primary_price']:,.4f}\n"
        f"Secondary Price: {spread['secondary_price']:,.4f}\n"
        f"Spread: {spread['spread_abs']:+.4f} ({spread['spread_pct']:+.4f}%)"
    )
    await _reply_with_chunks(update, response)


async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_report_command(update, context, "Usage: /market <symbol>", report_service.build_standard_report)


async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_report_command(update, context, "Usage: /signal <symbol>", report_service.build_signal_report)


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_report_command(update, context, "Usage: /summary <symbol>", report_service.build_executive_summary)


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_report_command(update, context, "Usage: /report <symbol>", report_service.build_document_report)


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return

    symbols = [item.strip().upper() for item in context.args if item.strip()]
    await _send_typing(update, context)
    try:
        response = await report_service.build_scan_report(symbols=symbols or None)
    except Exception as exc:
        await update.effective_message.reply_text(str(exc))
        return
    await _reply_with_chunks(update, response)


async def _run_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE, usage: str, builder) -> None:
    if update.effective_message is None:
        return
    if not context.args:
        await update.effective_message.reply_text(usage)
        return

    await _send_typing(update, context)
    try:
        report = await builder(context.args[0])
    except Exception as exc:
        await update.effective_message.reply_text(str(exc))
        return
    await _reply_with_chunks(update, report)


async def _send_typing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )


async def _reply_with_chunks(update: Update, text: str) -> None:
    if update.effective_message is None:
        return
    for chunk in chunk_text(text):
        await update.effective_message.reply_text(chunk)

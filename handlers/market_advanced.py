import inspect
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from services.market_engine import market_engine
from services.report_generator import report_generator

logger = logging.getLogger(__name__)
MAX_MESSAGE_LENGTH = 3900


async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Render the standard market intelligence report."""
    await _run_symbol_command(
        update,
        context,
        usage="Usage: /market <symbol>",
        renderer=report_generator.generate_market_report,
    )


async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Render the compact signal report."""
    await _run_symbol_command(
        update,
        context,
        usage="Usage: /signal <symbol>",
        renderer=report_generator.generate_signal_report,
    )


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Render the executive summary report."""
    await _run_symbol_command(
        update,
        context,
        usage="Usage: /summary <symbol>",
        renderer=report_generator.generate_summary_report,
    )


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Render the full document-style report."""
    await _run_symbol_command(
        update,
        context,
        usage="Usage: /report <symbol>",
        renderer=report_generator.generate_document_report,
    )


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run a watchlist scan across default or user-supplied symbols."""
    if update.effective_message is None:
        return

    symbols = [item.strip().upper() for item in context.args if item.strip()]
    await _send_typing(update, context)

    try:
        analyses = await market_engine.scan_market(symbols=symbols or None)
    except Exception as exc:
        logger.exception("Market scan failed.")
        await update.effective_message.reply_text(
            f"Unable to complete the market scan right now: {exc}"
        )
        return

    if not analyses:
        await update.effective_message.reply_text("No scan results were available.")
        return

    await _send_chunked_text(
        update,
        report_generator.generate_scan_report(analyses),
    )


async def _run_symbol_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    usage: str,
    renderer,
) -> None:
    """Shared execution path for symbol-based market commands."""
    if update.effective_message is None:
        return

    if not context.args:
        await update.effective_message.reply_text(usage)
        return

    symbol = context.args[0]
    await _send_typing(update, context)

    try:
        analysis = await market_engine.analyze_symbol(symbol)
        report = renderer(analysis)
        if inspect.isawaitable(report):
            report = await report
    except Exception as exc:
        logger.exception("Market analysis failed for %s", symbol)
        await update.effective_message.reply_text(
            f"Unable to build the market intelligence report for {symbol.upper()}: {exc}"
        )
        return

    await _send_chunked_text(update, report)


async def _send_typing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a typing action to Telegram while the command runs."""
    if update.effective_chat is None:
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )


async def _send_chunked_text(update: Update, text: str) -> None:
    """Send long messages in Telegram-safe chunks."""
    if update.effective_message is None:
        return

    for chunk in _chunk_text(text, MAX_MESSAGE_LENGTH):
        await update.effective_message.reply_text(chunk)


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split long report text into smaller messages."""
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

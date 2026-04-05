import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from services.alert_engine import alert_engine

logger = logging.getLogger(__name__)
MAX_MESSAGE_LENGTH = 3900


async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a one-off alert report for a symbol."""
    if update.effective_message is None:
        return

    if not context.args:
        await update.effective_message.reply_text("Usage: /alert <symbol>")
        return

    symbol = context.args[0]
    await _send_typing(update, context)

    try:
        report = await alert_engine.build_manual_alert_report(symbol)
    except Exception as exc:
        logger.exception("Manual alert generation failed for %s", symbol)
        await update.effective_message.reply_text(
            f"Unable to generate the alert report for {symbol.upper()}: {exc}"
        )
        return

    await _send_chunked_text(update, report)


async def alertset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Register a scheduled alert subscription for the current chat."""
    if update.effective_message is None:
        return

    if len(context.args) < 2:
        await update.effective_message.reply_text(
            "Usage: /alertset <symbol> <type>\nExample: /alertset BTC breakout"
        )
        return

    symbol, alert_type = context.args[0], context.args[1]

    try:
        subscription = alert_engine.set_alert_subscription(
            context.application.bot_data,
            update.effective_chat.id if update.effective_chat else 0,
            symbol,
            alert_type,
        )
    except Exception as exc:
        await update.effective_message.reply_text(str(exc))
        return

    await update.effective_message.reply_text(
        "Alert subscription saved.\n"
        f"Instrument: {subscription['symbol']}USDT\n"
        f"Active filters: {', '.join(subscription['types'])}"
    )


async def alertscan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scan either the current chat's subscriptions or a supplied symbol list."""
    if update.effective_message is None:
        return

    await _send_typing(update, context)

    if context.args:
        symbols = [item.strip().upper() for item in context.args if item.strip()]
    else:
        chat_id = update.effective_chat.id if update.effective_chat else 0
        symbols = list(alert_engine.get_chat_subscriptions(context.application.bot_data, chat_id).keys())

    try:
        report = await alert_engine.build_scan_report(symbols=symbols or None)
    except Exception as exc:
        logger.exception("Alert scan failed.")
        await update.effective_message.reply_text(
            f"Unable to complete the alert scan right now: {exc}"
        )
        return

    await _send_chunked_text(update, report)


async def _send_typing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a typing action while the alert command runs."""
    if update.effective_chat is None:
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )


async def _send_chunked_text(update: Update, text: str) -> None:
    """Send long alert messages in Telegram-safe chunks."""
    if update.effective_message is None:
        return

    for chunk in _chunk_text(text):
        await update.effective_message.reply_text(chunk)


def _chunk_text(text: str, chunk_size: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split long alert text into smaller messages."""
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

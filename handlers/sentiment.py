from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from services.news_service import news_service
from services.sentiment_service import sentiment_service
from utils.formatting import chunk_text


async def sentiment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show a simple sentiment snapshot."""
    if update.effective_message is None:
        return
    if not context.args:
        await update.effective_message.reply_text("Usage: /sentiment <symbol>")
        return

    await _send_typing(update, context)
    try:
        response = await sentiment_service.get_sentiment_report(context.args[0])
    except Exception as exc:
        await update.effective_message.reply_text(str(exc))
        return
    await _reply_with_chunks(update, response)


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show a compact news brief."""
    if update.effective_message is None:
        return

    symbol = context.args[0] if context.args else None
    await _send_typing(update, context)
    try:
        response = await news_service.get_news_brief(symbol)
    except Exception as exc:
        await update.effective_message.reply_text(str(exc))
        return
    await _reply_with_chunks(update, response)


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

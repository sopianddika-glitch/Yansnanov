from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from services.ai_service import ai_service
from utils.formatting import chunk_text
from utils.logger import get_logger

logger = get_logger(__name__)


async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a free-form Gemini response."""
    if update.effective_message is None:
        return

    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.effective_message.reply_text("Usage: /ai <prompt>")
        return

    await _send_typing(update, context)
    try:
        response = await ai_service.generate_response(prompt)
    except RuntimeError as exc:
        await update.effective_message.reply_text(str(exc))
        return
    await _reply_with_chunks(update, response)


async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Summarize arbitrary text."""
    if update.effective_message is None:
        return

    text = " ".join(context.args).strip()
    if not text:
        await update.effective_message.reply_text("Usage: /summarize <text>")
        return

    await _send_typing(update, context)
    try:
        summary = await ai_service.summarize_text(text)
    except RuntimeError as exc:
        await update.effective_message.reply_text(str(exc))
        return
    await _reply_with_chunks(update, summary)


async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Translate text into a target language."""
    if update.effective_message is None:
        return

    raw_text = " ".join(context.args).strip()
    if not raw_text:
        await update.effective_message.reply_text("Usage: /translate <language> | <text>")
        return

    if "|" in raw_text:
        language, text = [part.strip() for part in raw_text.split("|", maxsplit=1)]
    else:
        parts = raw_text.split(maxsplit=1)
        if len(parts) < 2:
            await update.effective_message.reply_text("Usage: /translate <language> | <text>")
            return
        language, text = parts[0], parts[1]

    await _send_typing(update, context)
    try:
        translated = await ai_service.translate_text(text, language)
    except RuntimeError as exc:
        await update.effective_message.reply_text(str(exc))
        return
    await _reply_with_chunks(update, translated)


async def _send_typing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a typing action while the AI request runs."""
    if update.effective_chat is None:
        return
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )


async def _reply_with_chunks(update: Update, text: str) -> None:
    """Send long text replies safely."""
    if update.effective_message is None:
        return
    for chunk in chunk_text(text):
        await update.effective_message.reply_text(chunk)

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from services.ai_service import ai_service

logger = logging.getLogger(__name__)
MAX_MESSAGE_LENGTH = 4000


async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a response from Gemini for the user's prompt."""
    if update.effective_message is None:
        return

    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.effective_message.reply_text("Usage: /ai <prompt>")
        return

    if update.effective_chat is not None:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

    try:
        response = await ai_service.generate_response(prompt)
    except RuntimeError as exc:
        logger.warning("AI request failed: %s", exc)
        await update.effective_message.reply_text(str(exc))
        return

    for chunk in _chunk_text(response, MAX_MESSAGE_LENGTH):
        await update.effective_message.reply_text(chunk)


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split long AI responses into Telegram-safe chunks."""
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

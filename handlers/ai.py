from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from services.ai_service import ai_service


async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.effective_message.reply_text("Usage: /ai <prompt>")
        return
    await _send_typing(update, context)
    reply = await ai_service.generate_response(prompt)
    await update.effective_message.reply_text(reply)


async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args).strip()
    if not text:
        await update.effective_message.reply_text("Usage: /summarize <text>")
        return
    await _send_typing(update, context)
    reply = await ai_service.summarize_text(text)
    await update.effective_message.reply_text(reply)


async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payload = " ".join(context.args).strip()
    if "|" not in payload:
        await update.effective_message.reply_text("Usage: /translate <language> | <text>")
        return
    target_language, text = [part.strip() for part in payload.split("|", maxsplit=1)]
    if not target_language or not text:
        await update.effective_message.reply_text("Usage: /translate <language> | <text>")
        return
    await _send_typing(update, context)
    reply = await ai_service.translate_text(text, target_language)
    await update.effective_message.reply_text(reply)


async def _send_typing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is not None:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

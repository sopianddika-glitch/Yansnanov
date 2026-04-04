import html
import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Issue a warning to the user whose message was replied to."""
    if update.effective_message is None:
        return

    replied_message = update.effective_message.reply_to_message
    if replied_message is None or replied_message.from_user is None:
        await update.effective_message.reply_text(
            "Reply to a user's message with /warn to issue a warning."
        )
        return

    warned_user = replied_message.from_user
    if warned_user.is_bot:
        await update.effective_message.reply_text("Bots cannot receive warnings.")
        return

    chat = update.effective_chat
    if chat is None:
        await update.effective_message.reply_text("This command is only available inside chats.")
        return

    warnings_store = context.application.bot_data.setdefault("warnings", {})
    chat_warnings = warnings_store.setdefault(chat.id, {})
    chat_warnings[warned_user.id] = chat_warnings.get(warned_user.id, 0) + 1
    total_warnings = chat_warnings[warned_user.id]

    reason = " ".join(context.args).strip()
    moderator = update.effective_user

    logger.info(
        "Warning issued in chat %s to user %s by user %s. Total warnings: %s",
        chat.id,
        warned_user.id,
        moderator.id if moderator else "unknown",
        total_warnings,
    )

    message = (
        f"⚠️ Warning issued to {warned_user.mention_html()}.\n"
        f"Total warnings: <b>{total_warnings}</b>"
    )

    if reason:
        message += f"\nReason: {html.escape(reason)}"

    if moderator is not None:
        message += f"\nIssued by: {moderator.mention_html()}"

    await update.effective_message.reply_text(message, parse_mode="HTML")

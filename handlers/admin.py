from telegram import Update
from telegram.ext import ContextTypes


RULES_TEXT = (
    "Community Rules\n"
    "- Be respectful.\n"
    "- No spam or scam links.\n"
    "- Keep discussion relevant to trading and markets.\n"
    "- Follow admin instructions."
)


async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display community rules."""
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(RULES_TEXT)


async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Issue a warning to a replied user."""
    if update.effective_message is None:
        return

    replied_message = update.effective_message.reply_to_message
    if replied_message is None or replied_message.from_user is None:
        await update.effective_message.reply_text("Reply to a user's message with /warn.")
        return

    warnings_store = context.application.bot_data.setdefault("warnings", {})
    warned_user_id = replied_message.from_user.id
    warnings_store[warned_user_id] = warnings_store.get(warned_user_id, 0) + 1
    await update.effective_message.reply_text(
        f"Warning issued to {replied_message.from_user.full_name}. Total warnings: {warnings_store[warned_user_id]}"
    )


async def clean_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete the replied message and the command message when possible."""
    if update.effective_message is None:
        return

    replied_message = update.effective_message.reply_to_message
    if replied_message is None:
        await update.effective_message.reply_text("Reply to a message you want me to clean.")
        return

    try:
        await replied_message.delete()
        await update.effective_message.delete()
    except Exception:
        await update.effective_message.reply_text("I could not delete that message. Check my admin permissions.")


async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pin the replied message."""
    if update.effective_message is None:
        return

    replied_message = update.effective_message.reply_to_message
    if replied_message is None:
        await update.effective_message.reply_text("Reply to a message you want me to pin.")
        return

    try:
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id,
            message_id=replied_message.message_id,
            disable_notification=True,
        )
        await update.effective_message.reply_text("Message pinned.")
    except Exception:
        await update.effective_message.reply_text("I could not pin that message. Check my admin permissions.")

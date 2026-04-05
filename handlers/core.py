from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from config import APP_TIMEZONE
from utils.formatting import chunk_text

HELP_TEXT = (
    "Yansnanov Bot Commands\n"
    "/start\n"
    "/help\n"
    "/id\n"
    "/ping\n"
    "/time\n"
    "/ai <prompt>\n"
    "/summarize <text>\n"
    "/translate <language> | <text>\n"
    "/price <symbol>\n"
    "/market <symbol>\n"
    "/signal <symbol>\n"
    "/summary <symbol>\n"
    "/report <symbol>\n"
    "/scan [symbols]\n"
    "/alert <symbol>\n"
    "/alertset <symbol> <type>\n"
    "/alertscan [symbols]\n"
    "/sentiment <symbol>\n"
    "/news [symbol]\n"
    "/rules\n"
    "/warn\n"
    "/clean\n"
    "/pin"
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a short welcome message."""
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(
        "Yansnanov is online.\nUse /help to see all available commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the full command list."""
    if update.effective_message is None:
        return

    for chunk in chunk_text(HELP_TEXT):
        await update.effective_message.reply_text(chunk)


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return chat and user identifiers."""
    if update.effective_message is None:
        return

    user_id = update.effective_user.id if update.effective_user else "unknown"
    chat_id = update.effective_chat.id if update.effective_chat else "unknown"
    await update.effective_message.reply_text(
        f"User ID: {user_id}\nChat ID: {chat_id}"
    )


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Basic health check command."""
    if update.effective_message is None:
        return
    await update.effective_message.reply_text("pong")


async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return bot clock information."""
    if update.effective_message is None:
        return

    now_utc = datetime.now(timezone.utc)
    try:
        local_time = now_utc.astimezone(ZoneInfo(APP_TIMEZONE))
        local_text = local_time.strftime(f"%Y-%m-%d %H:%M:%S {APP_TIMEZONE}")
    except Exception:
        local_text = f"Unavailable for timezone {APP_TIMEZONE}"

    await update.effective_message.reply_text(
        f"UTC Time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}\nLocal Time: {local_text}"
    )

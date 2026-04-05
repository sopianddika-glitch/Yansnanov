from telegram import Update
from telegram.ext import ContextTypes


HELP_TEXT = (
    "Available commands:\n"
    "/start - show the welcome message\n"
    "/help - show command usage\n"
    "/ai <prompt> - ask Gemini\n"
    "/summarize <text> - summarize text\n"
    "/translate <language> | <text> - translate text\n"
    "/price <symbol> - get the latest price\n"
    "/market <symbol> - show a market snapshot\n"
    "/signal <symbol> - show a compact signal\n"
    "/summary <symbol> - show an AI market summary\n"
    "/report <symbol> - show a full market report\n"
    "/scan - scan the watchlist\n"
    "/alert <symbol> - evaluate active alert conditions\n"
    "/alertset <symbol> <type> - register an alert\n"
    "/alertscan - scan registered alerts"
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is not None:
        await update.effective_message.reply_text(
            "Yansnanov is online.\n\n" + HELP_TEXT
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is not None:
        await update.effective_message.reply_text(HELP_TEXT)

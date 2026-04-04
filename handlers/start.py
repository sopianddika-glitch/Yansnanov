from telegram import Update
from telegram.ext import ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message with the bot's main commands."""
    if update.effective_message is None:
        return

    message = (
        "Welcome to <b>Yansnanov Bot</b>.\n\n"
        "Available commands:\n"
        "/start - Show this message\n"
        "/ai &lt;prompt&gt; - Ask Gemini AI a question\n"
        "/price &lt;symbol&gt; - Get the latest Binance price in USDT\n"
        "/warn - Reply to a user's message to issue a warning"
    )

    await update.effective_message.reply_text(message, parse_mode="HTML")

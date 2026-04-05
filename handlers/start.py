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
        "/market &lt;symbol&gt; - Generate the standard market intelligence report\n"
        "/signal &lt;symbol&gt; - Generate a compact directional signal\n"
        "/summary &lt;symbol&gt; - Generate an executive market summary\n"
        "/report &lt;symbol&gt; - Generate the full document-style report\n"
        "/scan - Scan the default watchlist for high-conviction setups\n"
        "/alert &lt;symbol&gt; - Generate the current advanced alert report\n"
        "/alertset &lt;symbol&gt; &lt;type&gt; - Register a scheduled alert filter\n"
        "/alertscan - Scan subscriptions or the default alert watchlist\n"
        "/warn - Reply to a user's message to issue a warning"
    )

    await update.effective_message.reply_text(message, parse_mode="HTML")

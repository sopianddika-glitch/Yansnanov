from utils.logger import setup_logging

setup_logging()

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
from handlers.admin import clean_command, pin_command, rules_command, warn_command
from handlers.ai import ai_command, summarize_command, translate_command
from handlers.alert import alert_command, alertscan_command, alertset_command
from handlers.core import help_command, id_command, ping_command, start_command, time_command
from handlers.errors import error_handler
from handlers.market import market_command, price_command, report_command, scan_command, signal_command, summary_command
from handlers.sentiment import news_command, sentiment_command
from utils.logger import get_logger

logger = get_logger(__name__)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to unsupported commands."""
    if update.effective_message is None:
        return

    await update.effective_message.reply_text(
        "Unknown command. Use /start to see the available commands."
    )


def build_application() -> Application:
    """Create the PTB v20+ application."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("time", time_command))
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CommandHandler("summarize", summarize_command))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("market", market_command))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("alert", alert_command))
    app.add_handler(CommandHandler("alertset", alertset_command))
    app.add_handler(CommandHandler("alertscan", alertscan_command))
    app.add_handler(CommandHandler("sentiment", sentiment_command))
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("warn", warn_command))
    app.add_handler(CommandHandler("clean", clean_command))
    app.add_handler(CommandHandler("pin", pin_command))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_error_handler(error_handler)

    return app


def main() -> None:
    """Start the bot with long polling."""
    logger.info("Starting Yansnanov with modular PTB v20 architecture")
    app = build_application()
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()

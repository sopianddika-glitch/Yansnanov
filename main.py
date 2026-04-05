from utils.logger import setup_logging

setup_logging()

import logging

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
from handlers.alert import alert_command, alertscan_command, alertset_command
from handlers.ai import ai_command
from handlers.community import warn_command
from handlers.errors import error_handler
from handlers.market_advanced import (
    market_command,
    report_command,
    scan_command,
    signal_command,
    summary_command,
)
from handlers.market import price_command
from handlers.nlp_router import natural_language_handler
from handlers.start import start_command
from utils.middleware import post_init

logger = logging.getLogger(__name__)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to unsupported commands."""
    if update.effective_message is None:
        return

    await update.effective_message.reply_text(
        "Unknown command. Use /start to see the available commands."
    )


def build_application() -> Application:
    """Create the PTB v20+ application."""
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("market", market_command))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("alert", alert_command))
    app.add_handler(CommandHandler("alertset", alertset_command))
    app.add_handler(CommandHandler("alertscan", alertscan_command))
    app.add_handler(CommandHandler("warn", warn_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, natural_language_handler))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_error_handler(error_handler)

    return app


def main() -> None:
    """Start the bot with long polling."""
    logger.info("Starting Yansnanov Bot with ApplicationBuilder polling")
    app = build_application()
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()

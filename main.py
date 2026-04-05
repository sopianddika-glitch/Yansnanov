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
from handlers.ai import ai_command
from handlers.community import warn_command
from handlers.errors import error_handler
from handlers.market import price_command
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
    app.add_handler(CommandHandler("warn", warn_command))
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

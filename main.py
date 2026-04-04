from utils.logger import setup_logging

setup_logging()

import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from config import BOT_TOKEN
from handlers.ai import ai_command
from handlers.community import warn_command
from handlers.errors import error_handler
from handlers.market import price_command
from handlers.start import start_command
from utils.middleware import post_init

logger = logging.getLogger(__name__)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply when the user sends a command that is not registered."""
    if update.effective_message is None:
        return

    await update.effective_message.reply_text(
        "I don't recognize that command yet. Use /start to see the available commands."
    )


def build_application():
    """Create and configure the Telegram application."""
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ai", ai_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_error_handler(error_handler)

    return application


def main() -> None:
    """Start the bot with long polling."""
    logger.info("Starting Yansnanov Bot")
    application = build_application()
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()

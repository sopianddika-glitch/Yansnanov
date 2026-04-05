from utils.logger import get_logger, setup_logging

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
from handlers.ai import ai_command, summarize_command, translate_command
from handlers.alert import alert_command
from handlers.alertscan import alertscan_command
from handlers.alertset import alertset_command
from handlers.errors import error_handler
from handlers.market import market_command, scan_command
from handlers.price import price_command
from handlers.report import report_command
from handlers.signal import signal_command
from handlers.start import help_command, start_command
from handlers.summary import summary_command
from utils.middleware import post_init

logger = get_logger(__name__)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(
        "Unknown command. Use /help to see the available commands."
    )


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
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
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_error_handler(error_handler)


def build_application() -> Application:
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    register_handlers(app)
    return app


def main() -> None:
    logger.info("Starting Yansnanov on python-telegram-bot with ApplicationBuilder")
    app = build_application()
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

import logging
import traceback

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log unexpected exceptions and send a friendly reply to the user."""
    if context.error is not None:
        stack_trace = "".join(
            traceback.format_exception(
                type(context.error),
                context.error,
                context.error.__traceback__,
            )
        )
        logger.error("Unhandled exception while processing an update:\n%s", stack_trace)
    else:
        logger.error("Unhandled exception while processing an update with no error object.")

    if isinstance(update, Update) and update.effective_message is not None:
        try:
            await update.effective_message.reply_text(
                "Something went wrong on my side. Please try again in a moment."
            )
        except Exception:
            logger.exception("Failed to send the fallback error message to the user.")

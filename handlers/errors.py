import traceback

from telegram import Update
from telegram.ext import ContextTypes

from utils.logger import get_logger

logger = get_logger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.error is not None:
        stack_trace = "".join(
            traceback.format_exception(
                type(context.error),
                context.error,
                context.error.__traceback__,
            )
        )
        logger.error("Unhandled exception:\n%s", stack_trace)
    if isinstance(update, Update) and update.effective_message is not None:
        await update.effective_message.reply_text(
            "Something went wrong while processing your request."
        )

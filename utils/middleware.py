from telegram.ext import Application

from utils.logger import get_logger

logger = get_logger(__name__)


async def post_init(application: Application) -> None:
    application.bot_data.setdefault("alerts", {})
    me = await application.bot.get_me()
    logger.info("Bot initialized as @%s", me.username)

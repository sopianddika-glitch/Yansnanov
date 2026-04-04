import logging

from telegram.ext import Application

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Run application setup tasks after the bot is initialized."""
    application.bot_data.setdefault("warnings", {})
    me = await application.bot.get_me()
    logger.info("Bot initialization complete for @%s", me.username)

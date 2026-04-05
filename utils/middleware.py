import logging

from telegram.ext import Application

from services.alert_engine import alert_engine
from services.alert_scheduler import configure_alert_scheduler

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Run application setup tasks after the bot is initialized."""
    application.bot_data.setdefault("warnings", {})
    alert_engine.initialize_state(application.bot_data)
    configure_alert_scheduler(application)
    me = await application.bot.get_me()
    logger.info("Bot initialization complete for @%s", me.username)

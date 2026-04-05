import logging
from datetime import timedelta

from telegram.ext import Application, CallbackContext

from services.alert_engine import alert_engine

logger = logging.getLogger(__name__)
SCHEDULE_NAME = "advanced_market_alert_scan"
SCAN_INTERVAL = timedelta(minutes=10)
INITIAL_DELAY = timedelta(minutes=1)


async def scheduled_alert_scan(context: CallbackContext) -> None:
    """Run the periodic alert scan and deliver triggered messages."""
    deliveries = await alert_engine.collect_scheduled_deliveries(context.application)
    for chat_id, message in deliveries:
        for chunk in _chunk_text(message):
            await context.bot.send_message(chat_id=chat_id, text=chunk)


def configure_alert_scheduler(application: Application) -> None:
    """Register the repeating alert job on the PTB job queue."""
    alert_engine.initialize_state(application.bot_data)

    if application.job_queue is None:
        logger.warning("Alert scheduler could not start because the PTB JobQueue is unavailable.")
        return

    existing_job = application.job_queue.get_jobs_by_name(SCHEDULE_NAME)
    if existing_job:
        logger.info("Alert scheduler job already configured.")
        return

    application.job_queue.run_repeating(
        scheduled_alert_scan,
        interval=SCAN_INTERVAL,
        first=INITIAL_DELAY,
        name=SCHEDULE_NAME,
    )
    logger.info("Alert scheduler configured with interval %s minutes.", SCAN_INTERVAL.total_seconds() / 60)


def _chunk_text(text: str, chunk_size: int = 3900) -> list[str]:
    """Split long scheduled messages into Telegram-safe chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if end < len(text):
            split_at = chunk.rfind("\n")
            if split_at > chunk_size // 2:
                end = start + split_at
                chunk = text[start:end]
        chunks.append(chunk.strip())
        start = end

    return [chunk for chunk in chunks if chunk]

import logging

from telegram import Update
from telegram.ext import ContextTypes

from services.market_service import market_service

logger = logging.getLogger(__name__)


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch and display a Binance price for a token against USDT."""
    if update.effective_message is None:
        return

    if not context.args:
        await update.effective_message.reply_text("Usage: /price <symbol>")
        return

    symbol = context.args[0]

    try:
        pair, price = await market_service.get_price(symbol)
    except ValueError as exc:
        await update.effective_message.reply_text(str(exc))
        return
    except RuntimeError as exc:
        logger.warning("Market request failed: %s", exc)
        await update.effective_message.reply_text(str(exc))
        return

    formatted_price = _format_price(price)
    await update.effective_message.reply_text(
        f"📈 <b>{pair}</b>\nCurrent price: <code>${formatted_price}</code>",
        parse_mode="HTML",
    )


def _format_price(price: float) -> str:
    """Format the price for a cleaner Telegram response."""
    formatted = f"{price:,.8f}".rstrip("0").rstrip(".")
    return formatted or "0"

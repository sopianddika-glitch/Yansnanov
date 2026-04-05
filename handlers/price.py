from telegram import Update
from telegram.ext import ContextTypes

from services.market_service import market_service


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    symbol = _symbol_from_args(context.args)
    if not symbol:
        await update.effective_message.reply_text("Usage: /price <symbol>")
        return
    quote = await market_service.get_price(symbol)
    await update.effective_message.reply_text(market_service.format_price_text(quote))


def _symbol_from_args(args: list[str]) -> str | None:
    return args[0].strip() if args else None

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from services.ai_service import ai_service
from services.market_service import market_service


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    symbol = _symbol_from_args(context.args)
    if not symbol:
        await update.effective_message.reply_text("Usage: /summary <symbol>")
        return
    await _send_typing(update, context)
    snapshot = await market_service.get_market_snapshot(symbol)
    context_text = market_service.format_summary_context(snapshot)
    try:
        reply = await ai_service.summarize_market(context_text)
    except RuntimeError:
        reply = market_service.format_fallback_summary(snapshot)
    await update.effective_message.reply_text(reply)


async def _send_typing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is not None:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )


def _symbol_from_args(args: list[str]) -> str | None:
    return args[0].strip() if args else None

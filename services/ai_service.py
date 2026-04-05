import google.genai as genai

from config import AI_KEY
from utils.logger import get_logger

logger = get_logger(__name__)
MODEL_NAME = "gemini-2.0-flash"


class AIService:
    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    async def generate_response(self, prompt: str) -> str:
        prompt = prompt.strip()
        if not prompt:
            raise RuntimeError("Please provide a prompt.")
        try:
            response = await self._client.aio.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("Gemini request failed")
            raise RuntimeError("The AI service is temporarily unavailable.") from exc
        text = getattr(response, "text", "") or ""
        if text.strip():
            return text.strip()
        raise RuntimeError("The AI service returned an empty response.")

    async def summarize_text(self, text: str) -> str:
        return await self.generate_response(
            "Summarize the following content in a concise professional style:\n\n"
            f"{text.strip()}"
        )

    async def translate_text(self, text: str, target_language: str) -> str:
        return await self.generate_response(
            f"Translate the following text to {target_language}. Preserve financial terminology.\n\n"
            f"{text.strip()}"
        )

    async def summarize_market(self, market_context: str) -> str:
        return await self.generate_response(
            "You are a market analyst. Summarize this market snapshot with a clear bias, "
            "key risk, and short actionable takeaway.\n\n"
            f"{market_context.strip()}"
        )

    async def draft_market_report(self, market_context: str) -> str:
        return await self.generate_response(
            "Write a structured market report with sections for price action, bias, risk, "
            "and watchpoints using the following market data.\n\n"
            f"{market_context.strip()}"
        )


ai_service = AIService(AI_KEY)

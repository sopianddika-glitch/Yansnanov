import logging

import google.genai as genai

from config import AI_KEY

logger = logging.getLogger(__name__)
PRIMARY_MODEL = "gemini-2.0-flash"
FALLBACK_MODEL = "gemini-2.5-flash"


class GeminiAIService:
    """Async wrapper for the Google Gen AI SDK."""

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    async def generate_response(self, prompt: str) -> str:
        """Generate a Gemini response for the provided prompt."""
        prompt = prompt.strip()
        if not prompt:
            raise RuntimeError("Please provide a prompt for the AI service.")

        for model_name in (PRIMARY_MODEL, FALLBACK_MODEL):
            try:
                response = await self._client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
            except Exception as exc:
                logger.warning("Gemini request failed for model %s: %s", model_name, exc)
                continue

            text = self._extract_text(response)
            if text:
                return text

            logger.warning("Gemini model %s returned an empty response.", model_name)

        raise RuntimeError("The AI service is temporarily unavailable. Please try again later.")

    @staticmethod
    def _extract_text(response) -> str:
        """Extract text from a Gemini response object."""
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        fragments: list[str] = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    fragments.append(part_text.strip())

        return "\n".join(fragments).strip()


ai_service = GeminiAIService(AI_KEY)

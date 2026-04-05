import logging

import google.genai as genai

from config import AI_KEY

logger = logging.getLogger(__name__)
DEFAULT_MODEL_SEQUENCE = ("gemini-2.0-flash", "gemini-2.5-flash")


class GeminiAIService:
    """Service wrapper around the Google Gen AI SDK."""

    def __init__(self, api_key: str, model_names: tuple[str, ...] = DEFAULT_MODEL_SEQUENCE) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model_names = model_names

    async def generate_response(self, prompt: str) -> str:
        """Generate a response using the new google-genai SDK."""
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise RuntimeError("Please provide a prompt for the AI service.")

        last_error: Exception | None = None

        for model_name in self._model_names:
            try:
                response = await self._client.aio.models.generate_content(
                    model=model_name,
                    contents=normalized_prompt,
                )
            except Exception as exc:
                last_error = exc
                logger.warning("Gemini request failed for model %s: %s", model_name, exc)
                continue

            text = self._extract_text(response)
            if text:
                return text

            logger.warning("Gemini model %s returned an empty response.", model_name)

        if last_error is not None:
            logger.error("All Gemini model attempts failed. Last error: %s", last_error)

        raise RuntimeError("The AI service is temporarily unavailable. Please try again later.")

    @staticmethod
    def _extract_text(response) -> str:
        """Extract text from a Google Gen AI response."""
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        fragments = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", None)
                if part_text:
                    fragments.append(part_text.strip())

        return "\n".join(fragment for fragment in fragments if fragment).strip()


ai_service = GeminiAIService(AI_KEY)

import asyncio
import logging

import google.generativeai as genai

from config import AI_KEY

logger = logging.getLogger(__name__)


class GeminiAIService:
    """Service wrapper around the Gemini text generation API."""

    def __init__(self, api_key: str, model_name: str = "gemini-pro") -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)

    async def generate_response(self, prompt: str) -> str:
        """Generate a text response without blocking the event loop."""
        try:
            return await asyncio.to_thread(self._generate_response_sync, prompt)
        except RuntimeError:
            raise
        except Exception as exc:
            logger.exception("Unexpected Gemini client error.")
            raise RuntimeError("The AI service is temporarily unavailable. Please try again later.") from exc

    def _generate_response_sync(self, prompt: str) -> str:
        """Call Gemini synchronously and normalize the returned text."""
        response = self._model.generate_content(prompt)
        text = self._extract_text(response)
        if not text:
            raise RuntimeError("The AI service returned an empty response. Please try again.")
        return text

    @staticmethod
    def _extract_text(response) -> str:
        """Extract text from Gemini responses, including fallback candidate parsing."""
        try:
            text = response.text
            if text:
                return text.strip()
        except Exception:
            logger.debug("Gemini response.text was unavailable, trying candidate fallback.")

        fragments = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", None)
                if part_text:
                    fragments.append(part_text.strip())

        return "\n".join(fragment for fragment in fragments if fragment).strip()


ai_service = GeminiAIService(AI_KEY)

import logging

import google.genai as genai

from config import AI_KEY
from utils.logger import get_logger

logger = get_logger(__name__)
MODEL_NAME = "gemini-2.0-flash"


class GeminiAIService:
    """Async wrapper for the Google Gen AI SDK."""

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    async def generate_response(self, prompt: str) -> str:
        """Generate a Gemini response for the provided prompt."""
        prompt = prompt.strip()
        if not prompt:
            raise RuntimeError("Please provide a prompt for the AI service.")

        try:
            response = await self._client.aio.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
        except Exception as exc:
            logger.warning("Gemini request failed for model %s: %s", MODEL_NAME, exc)
            raise RuntimeError("The AI service is temporarily unavailable. Please try again later.") from exc

        text = self._extract_text(response)
        if text:
            return text

        raise RuntimeError("The AI service returned an empty response. Please try again later.")

    async def summarize_text(self, text: str) -> str:
        """Summarize arbitrary input text."""
        prompt = (
            "Summarize the following text in a concise, professional way.\n\n"
            f"{text.strip()}"
        )
        return await self.generate_response(prompt)

    async def translate_text(self, text: str, target_language: str) -> str:
        """Translate text into the requested target language."""
        prompt = (
            f"Translate the following text into {target_language}. "
            "Keep the meaning precise and preserve any financial terms.\n\n"
            f"{text.strip()}"
        )
        return await self.generate_response(prompt)

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

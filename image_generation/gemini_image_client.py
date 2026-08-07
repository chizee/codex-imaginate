"""Gemini 2.5 Flash Image (Nano Banana) client with same interface as Qwen.

Uses the google.genai SDK for image generation.
Returns list[dict] with "url" key matching QwenClient.generate_image() interface.
"""

import os
import base64
import logging
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

# Gemini image model ID
GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image"


class GeminiImageClient:
    """Gemini Nano Banana image generation wrapper.

    Implements the same ``generate_image(prompt) -> list[dict]``
    interface as QwenClient so it's a drop-in replacement.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Add it to .env or set the environment variable."
            )
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise RuntimeError(
                    "google-genai SDK not installed. Run: pip install google-genai"
                )
        return self._client

    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        n: int = 1,
    ) -> list[dict]:
        """Generate image(s) via Gemini 2.5 Flash Image.

        Args:
            prompt: Text description of the desired image.
            size: Ignored — Gemini outputs 1024x1024 by default.
            n: Number of images (Gemini returns 1 per call).

        Returns:
            List of dicts with key "url" containing a data URI or file path.
        """
        try:
            response = self.model.models.generate_content(
                model=GEMINI_IMAGE_MODEL,
                contents=prompt,
                config={
                    "response_modalities": ["IMAGE", "TEXT"],
                },
            )

            results = []
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        img_data = part.inline_data.data
                        b64 = base64.b64encode(img_data).decode("utf-8")
                        mime = part.inline_data.mime_type or "image/png"
                        data_uri = f"data:{mime};base64,{b64}"
                        results.append({"url": data_uri})
                    elif hasattr(part, "text") and part.text:
                        logger.debug("Gemini text response: %s", part.text[:100])

            if not results:
                logger.warning("Gemini returned no image data for prompt: %s", prompt[:60])

            return results

        except Exception as exc:
            error_str = str(exc).lower()
            if "quota" in error_str or "resource_exhausted" in error_str or "429" in error_str:
                logger.warning("Gemini quota exhausted: %s", exc)
            else:
                logger.error("Gemini image generation failed: %s", exc)
            raise  # Let caller handle fallback


def is_gemini_available() -> bool:
    """Check if Gemini is configured and likely to work."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return False
    try:
        import google.genai
        return True
    except ImportError:
        return False

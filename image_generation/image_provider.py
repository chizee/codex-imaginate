"""Unified image provider — Gemini 2.5 Flash Image primary, Qwen fallback.

Tries Gemini first. If Gemini fails (quota, network, SDK error),
falls back to Qwen-image-2.0-pro via the existing QwenClient pipeline.
"""

import os
import logging
from typing import Optional

from agent_orchestrator.qwen_client import QwenClient
from image_generation.gemini_image_client import GeminiImageClient, is_gemini_available

logger = logging.getLogger(__name__)


class ImageProvider:
    """Wrapper that tries Gemini first, then falls back to Qwen.

    Usage in qwen_image_client.py / reference_manager.py:
        provider = ImageProvider()
        results = provider.generate_image(prompt=prompt)
    """

    def __init__(self, qwen_client: Optional[QwenClient] = None):
        self.qwen_client = qwen_client or QwenClient()
        self.gemini_client = None

        if is_gemini_available():
            try:
                self.gemini_client = GeminiImageClient()
                logger.info("Gemini Nano Banana available — will use as primary")
            except ValueError as exc:
                logger.info("Gemini not configured: %s — using Qwen only", exc)
        else:
            logger.info("Gemini SDK not installed — using Qwen only")

    def generate_image(self, prompt: str) -> list[dict]:
        """Generate image — Gemini first, Qwen fallback.

        Args:
            prompt: Text description of the desired image.

        Returns:
            List of dicts with key "url".
        """
        # Try Gemini first
        if self.gemini_client is not None:
            try:
                results = self.gemini_client.generate_image(prompt=prompt)
                if results:
                    logger.debug("Gemini generated image for: %s", prompt[:60])
                    return results
                logger.info("Gemini returned empty, falling back to Qwen")
            except Exception as exc:
                logger.info(
                    "Gemini failed (%s), falling back to Qwen: %s",
                    type(exc).__name__, exc,
                )

        # Fallback to Qwen
        logger.debug("Using Qwen for: %s", prompt[:60])
        return self.qwen_client.generate_image(prompt=prompt)

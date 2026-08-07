"""Reusable Qwen Cloud API client via OpenAI-compatible SDK.

Supports:
- Chat completions (qwen3.7-max / qwen3.7-plus / qwen3.6-flash)
- Image generation (qwen-image-2.0-pro)
- Transcription / future modalities
"""

import time
import logging
from typing import Optional

from openai import OpenAI, APIError, RateLimitError, APITimeoutError

from shared.config.settings import settings

logger = logging.getLogger(__name__)


class QwenClient:
    """Thread-safe Qwen Cloud client with automatic retry logic."""

    _last_img_time: float = 0.0

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.DASHSCOPE_API_KEY
        if not self.api_key:
            raise ValueError(
                "DASHSCOPE_API_KEY is not set. "
                "Add it to .env or set the environment variable."
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=settings.QWEN_BASE_URL,
        )

    # ------------------------------------------------------------------
    # Chat completions
    # ------------------------------------------------------------------

    def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: str = "",
        response_format: Optional[dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat completion request to Qwen.

        Args:
            prompt: User message content.
            system: Optional system message.
            model: Model name (defaults to qwen3.7-max).
            response_format: e.g. {"type": "json_object"}.
            temperature: Sampling temperature.
            max_tokens: Max tokens in response.

        Returns:
            The text content of the model's reply.
        """
        model = model or settings.LLM_MODEL
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if response_format:
            kwargs["response_format"] = response_format

        last_error = None
        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            except (RateLimitError, APITimeoutError, APIError) as exc:
                last_error = exc
                logger.warning(
                    "Qwen API attempt %d/%d failed: %s",
                    attempt, settings.MAX_RETRIES, exc,
                )
                if attempt < settings.MAX_RETRIES:
                    time.sleep(settings.RETRY_BACKOFF * attempt)
            except Exception as exc:
                last_error = exc
                logger.error("Qwen API unexpected error: %s", exc)
                raise

        raise RuntimeError(
            f"Qwen API failed after {settings.MAX_RETRIES} retries: {last_error}"
        )

    # ------------------------------------------------------------------
    # Structured JSON output (wrapper around chat with response_format)
    # ------------------------------------------------------------------

    def chat_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: str = "",
        temperature: float = 0.3,
    ) -> str:
        """Request a JSON response from the model."""
        return self.chat(
            prompt=prompt,
            system=system,
            model=model or settings.LLM_MODEL,
            response_format={"type": "json_object"},
            temperature=temperature,
        )

    # ------------------------------------------------------------------
    # Image generation
    # ------------------------------------------------------------------

    def generate_image(
        self,
        prompt: str,
        model: str = "",
        size: str = "",
        n: int = 1,
        seed: Optional[int] = None,
        image: Optional[str] = None,  # base64 data URI for ref images
    ) -> list[dict]:
        """Generate an image via Qwen Image 2.0 Pro (multimodal generation endpoint).

        Uses POST /api/v1/services/aigc/multimodal-generation/generation
        with the messages format (chat-compatible). Throttles to 1 req/3s.

        Args:
            prompt: Text description of the desired image.
            model: Model override.
            size: e.g. "1024x1024".
            n: Number of images (ignored — model returns 1).
            seed: Ignored.
            image: base64 data URI for reference image (character consistency).

        Returns:
            List of dicts with keys: url.
        """
        import requests as http_requests
        import time as _tm

        # Rate limiting: workspace endpoint ~4 images/min = 15s between
        elapsed = _tm.time() - QwenClient._last_img_time
        if elapsed < 15.0:
            _tm.sleep(15.0 - elapsed)
        QwenClient._last_img_time = _tm.time()

        model = model or settings.IMAGE_MODEL
        size = size or settings.IMAGE_SIZE
        width, height = (int(x) for x in size.split("x"))

        content = [{"type": "text", "text": prompt}]
        if image:
            content.append({"type": "image_url", "image_url": {"url": image}})

        payload = {
            "model": model,
            "input": {
                "messages": [
                    {"role": "user", "content": content}
                ]
            },
            "parameters": {
                "size": f"{width}*{height}",
            },
        }

        url = f"{settings.QWEN_DASHSCOPE_BASE}/services/aigc/multimodal-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error = None
        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                resp = http_requests.post(url, headers=headers, json=payload, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                results = []
                choices = data.get("output", {}).get("choices", [])
                for choice in choices:
                    msg = choice.get("message", {})
                    content_list = msg.get("content", [])
                    for item in content_list:
                        if "image" in item:
                            results.append({"url": item["image"]})
                return results
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Qwen image attempt %d/%d failed: %s",
                    attempt, settings.MAX_RETRIES, exc,
                )
                if attempt < settings.MAX_RETRIES:
                    # On 429, back off more aggressively (image endpoint is
                    # QPS-limited and needs a longer cooldown).
                    if "429" in str(exc):
                        _tm.sleep(settings.IMAGE_429_BACKOFF * attempt)
                    else:
                        _tm.sleep(settings.RETRY_BACKOFF * attempt)

        raise RuntimeError(
            f"Qwen image API failed after {settings.MAX_RETRIES} retries: {last_error}"
        )

    # ------------------------------------------------------------------
    # TTS — CosyVoice (uses REST API, not OpenAI-compatible)
    # ------------------------------------------------------------------

    def generate_speech(
        self,
        text: str,
        voice: str = "",
        model: str = "",
        speed: float = 1.0,
        sample_rate: int = 0,
    ) -> bytes:
        """Generate speech audio via CosyVoice v3-plus.

        Args:
            text: Text to narrate.
            voice: Voice ID (default from settings).
            model: Model override.
            speed: Speaking speed (0.5-2.0).
            sample_rate: Audio sample rate.

        Returns:
            Raw MP3 bytes.
        """
        import requests as http_requests

        model = model or settings.TTS_MODEL
        voice = voice or settings.TTS_VOICE
        sample_rate = sample_rate or settings.TTS_SAMPLE_RATE

        url = settings.COSYVOICE_URL
        payload = {
            "model": model,
            "input": {
                "text": text,
                "voice": voice,
                "speed": speed,
            },
            "parameters": {
                "format": "mp3",
                "sample_rate": sample_rate,
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error = None
        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                resp = http_requests.post(url, headers=headers, json=payload, timeout=120)
                resp.raise_for_status()
                return resp.content
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "TTS attempt %d/%d failed: %s",
                    attempt, settings.MAX_RETRIES, exc,
                )
                if attempt < settings.MAX_RETRIES:
                    time.sleep(settings.RETRY_BACKOFF * attempt)

        raise RuntimeError(
            f"TTS API failed after {settings.MAX_RETRIES} retries: {last_error}"
        )

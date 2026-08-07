"""Application configuration loaded from environment / .env file."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central config for Imaginate — all Qwen Cloud API settings."""

    # Qwen Cloud API key (workspace key for full model access)
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")

    # OpenAI-compatible endpoint (for chat completions)
    QWEN_BASE_URL: str = os.getenv(
        "QWEN_API_BASE",
        "https://ws-s8blchl8lx57ttc9.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
    )

    # Native DashScope endpoint (for image gen, TTS via multimodal)
    QWEN_DASHSCOPE_BASE: str = os.getenv(
        "QWEN_DASHSCOPE_BASE",
        "https://ws-s8blchl8lx57ttc9.ap-southeast-1.maas.aliyuncs.com/api/v1",
    )

    # Default models
    LLM_MODEL: str = "qwen3.6-flash"
    FAST_LLM_MODEL: str = "qwen3.6-flash"
    IMAGE_MODEL: str = "qwen-image-2.0-pro"
    TTS_MODEL: str = "qwen3-tts-instruct-flash"
    VIDEO_MODEL: str = "wan2.7-i2v"

    # Gemini API key (optional — used as primary image provider when set)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Retry settings
    MAX_RETRIES: int = 3
    RETRY_BACKOFF: float = 3.0

    # Image settings
    IMAGE_SIZE: str = "1024x1024"
    # Seconds to sleep between scene image calls. DashScope multimodal endpoint
    # is QPS-limited (~0.2-0.5 req/s); pacing avoids hammering it into 429s.
    IMAGE_SCENE_PACING: float = 38.0
    # Longer 429 backoff for the multimodal (image) endpoint specifically.
    IMAGE_429_BACKOFF: float = 45.0

    # TTS settings
    TTS_VOICE: str = "Ethan"  # Warm American male voice. Options: Ethan, Serena, Cherry (Instruct+Flash); Jennifer, Aiden (Flash only)
    TTS_SAMPLE_RATE: int = 24000

    # Output
    OUTPUT_DIR: str = "stories"

    # Pipeline
    PIPELINE_TIMEOUT: int = 600


settings = Settings()

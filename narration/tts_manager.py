"""Audio manager — voice selection, emotion tagging, and batch generation control.

Provides multiple English-accent voices and a voice-selector for storybook narration.
"""

import logging
from typing import Optional

from shared.models.story import Story
from narration.cosyvoice_client import generate_narration

logger = logging.getLogger(__name__)

VOICE_PROFILES = {
    "ethan": {
        "name": "Ethan",
        "gender": "male",
        "accent": "American",
        "style": "warm, energetic, vibrant",
        "description": "Warm American male voice — great for kids stories and adventure tales",
    },
    "serena": {
        "name": "Serena",
        "gender": "female",
        "accent": "American",
        "style": "gentle, calm, soothing",
        "description": "Gentle female voice — perfect for bedtime stories",
    },
    "cherry": {
        "name": "Cherry",
        "gender": "female",
        "accent": "American",
        "style": "sunny, positive, friendly",
        "description": "Sunny female voice — good for cheerful stories",
    },
}

DEFAULT_VOICE = "ethan"


def list_voices() -> list[dict]:
    """Return all available voice profiles."""
    return [{"id": vid, **profile} for vid, profile in VOICE_PROFILES.items()]


def generate_narration_with_voice(
    story: Story,
    voice_id: str = "",
    api_key: str = "",
) -> dict:
    """Generate narration for all scenes using the specified voice.

    Args:
        story: The Story object.
        voice_id: Voice profile ID (ethan, serena, cherry).
        api_key: DashScope API key.

    Returns:
        Dict mapping scene index to local MP3 path.
    """
    voice_id = voice_id or DEFAULT_VOICE
    profile = VOICE_PROFILES.get(voice_id, VOICE_PROFILES[DEFAULT_VOICE])
    logger.info("Using voice: %s (%s)", profile["name"], profile["accent"])
    return generate_narration(story=story, voice=profile["name"], api_key=api_key)
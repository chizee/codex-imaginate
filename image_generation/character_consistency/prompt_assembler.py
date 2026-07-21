"""Builds scene image prompts that maintain character consistency.

Character visual descriptions from the bible are embedded in each scene
prompt to maintain consistency (reference images are not supported on
the workspace multimodal endpoint).
"""

import logging
from shared.models.story import Scene, CharacterBible

logger = logging.getLogger(__name__)


def build_scene_prompt(scene: Scene, bible: CharacterBible) -> str:
    """Build a text prompt for image generation of a single scene.

    Includes character appearance descriptions from the bible for
    visual consistency across scenes.

    Args:
        scene: The scene to illustrate.
        bible: The story's character bible.

    Returns:
        A concise image generation prompt.
    """
    parts = []

    # Character appearance details from bible for consistency
    if scene.characters:
        char_descs = []
        for name in scene.characters:
            char = bible.get_character(name)
            if char and char.appearance:
                char_descs.append(f"{name}: {char.appearance}")
        if char_descs:
            parts.append("Characters: " + "; ".join(char_descs))

    # Scene action / description
    if scene.description:
        parts.append(scene.description.strip().rstrip("."))

    # Characters present
    if scene.characters:
        char_list = ", ".join(scene.characters)
        parts.append(f"featuring {char_list}")

    # Location
    if scene.location:
        if scene.location in bible.locations:
            parts.append(f"at {scene.location}")
        else:
            parts.append(f"setting: {scene.location}")

    # Mood / lighting
    if scene.mood and scene.mood != "neutral":
        mood_desc = _mood_to_atmosphere(scene.mood)
        parts.append(mood_desc)

    # Visual style
    if bible.visual_style:
        parts.append(bible.visual_style)

    prompt = ", ".join(parts)
    logger.debug("Scene %d prompt: %s", scene.index, prompt[:120])
    return prompt


def build_reference_prompt(character_name: str, appearance: str, visual_style: str) -> str:
    """Build a prompt for a character reference image (neutral, full-body).

    Args:
        character_name: The character's name.
        appearance: Full appearance description from bible.
        visual_style: The story's visual style.

    Returns:
        A prompt for a neutral reference image.
    """
    return (
        f"A full-body portrait of {character_name}, {appearance}, "
        f"standing in a neutral pose, plain light background, "
        f"front view, good lighting, {visual_style}"
    )


def _mood_to_atmosphere(mood: str) -> str:
    """Map story mood to image atmosphere description."""
    mapping = {
        "happy": "bright and warm atmosphere, golden lighting",
        "sad": "soft cool lighting, gentle shadows, melancholy atmosphere",
        "angry": "harsh lighting, dramatic shadows, intense atmosphere",
        "fearful": "dim lighting, long shadows, tense atmosphere",
        "surprised": "bright flash lighting, wide view, dramatic reveal",
        "mysterious": "foggy atmosphere, soft diffused light, secretive mood",
        "calm": "soft warm light, peaceful atmosphere, gentle colors",
        "exciting": "dynamic lighting, vibrant colors, energetic feel",
        "peaceful": "golden hour lighting, serene atmosphere, soft focus",
        "tense": "dramatic shadows, contrasty lighting, suspenseful feel",
        "hopeful": "warm golden light, soft glow, uplifting atmosphere",
    }
    return mapping.get(mood.lower(), f"{mood} atmosphere")

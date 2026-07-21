"""Classifies scene continuity to determine reference image strategy.

Continuity classes:
- HARD_CUT: New location or mood shift — use character refs only, no previous scene ref.
- SOFT_CUT: Same location, next moment — include previous scene as primary reference.
- STATE_RESET: Character state changed (got wet, changed clothes) — update bible, no previous ref.
"""

import logging
from shared.models.story import Scene

logger = logging.getLogger(__name__)


def classify_continuity(current: Scene, previous: Scene | None) -> str:
    """Determine the continuity class between two consecutive scenes.

    Args:
        current: The current scene.
        previous: The immediately previous scene (None for first scene).

    Returns:
        "HARD_CUT", "SOFT_CUT", or "STATE_RESET".
    """
    if previous is None:
        return "HARD_CUT"

    # Location change → HARD_CUT
    if current.location and previous.location:
        if current.location.lower() != previous.location.lower():
            logger.debug("HARD_CUT: location changed '%s' → '%s'",
                         previous.location, current.location)
            return "HARD_CUT"

    # Mood shift → HARD_CUT
    mood_shift = {"happy", "sad", "angry", "fearful", "surprised", "mysterious",
                  "calm", "exciting", "peaceful", "tense", "hopeful"}
    if current.mood and previous.mood:
        if current.mood.lower() != previous.mood.lower():
            if previous.mood.lower() in mood_shift:
                logger.debug("HARD_CUT: mood shift '%s' → '%s'",
                             previous.mood, current.mood)
                return "HARD_CUT"

    # State change detected → STATE_RESET
    if current.state_changes and current.state_changes != previous.state_changes:
        logger.debug("STATE_RESET: character state changed")
        return "STATE_RESET"

    # Default: same location, continuing moment → SOFT_CUT
    return "SOFT_CUT"

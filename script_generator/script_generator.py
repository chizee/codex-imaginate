"""Phase 1: Generates a complete story script from a user prompt via Qwen3.7-max structured output."""

import json
import os
import re
import logging
from typing import Optional

from agent_orchestrator.qwen_client import QwenClient
from shared.models.story import Story, Scene, Character, CharacterBible

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_KIDS = """You are a warm, imaginative children's story writer.
Write a short, engaging story (5-10 scenes) based on the user's idea.
Keep language simple and vivid. Each scene should fit on one phone screen.
Always end with a warm, positive message.

Output valid JSON only with this structure:
{
  "title": "Story title",
  "characters": [
    {
      "name": "Character name",
      "age": "age or age group",
      "role": "protagonist/sidekick/antagonist/etc",
      "appearance": "detailed visual description — hair color, skin tone, eye color, clothing, accessories, distinctive features",
      "personality": "personality traits",
      "notes": "any special notes"
    }
  ],
  "scenes": [
    {
      "index": 1,
      "title": "Scene title",
      "text": "The narration text for this scene — 2-4 sentences that will be read aloud",
      "description": "Visual description for illustration — describe what's SEEN only (characters, poses, expressions, background, lighting, colors). Do NOT use text/speech bubbles.",
      "location": "Where this scene takes place",
      "characters": ["CharacterName"],
      "mood": "mood/atmosphere"
    }
  ],
  "visual_style": "art style description for illustrations",
  "locations": {
    "location_name": "visual description of this location"
  }
}
"""

SYSTEM_PROMPT_ADULT = """You are a creative fiction writer capable of any genre.
Write a compelling short story (5-10 scenes) based on the user's idea.
Keep each scene's narration to 2-4 sentences that will be read aloud.

Output valid JSON only with this exact structure:
{
  "title": "Story title",
  "characters": [
    {
      "name": "Character name",
      "age": "age or age group",
      "role": "protagonist/sidekick/antagonist/etc",
      "appearance": "detailed visual description — hair color, skin tone, eye color, clothing, accessories, distinctive features",
      "personality": "personality traits",
      "notes": "any special notes"
    }
  ],
  "scenes": [
    {
      "index": 1,
      "title": "Scene title",
      "text": "The narration text for this scene — 2-4 sentences that will be read aloud",
      "description": "Visual description for illustration — describe what's SEEN only (characters, poses, expressions, background, lighting, colors). Do NOT use text/speech bubbles.",
      "location": "Where this scene takes place",
      "characters": ["CharacterName"],
      "mood": "mood/atmosphere"
    }
  ],
  "visual_style": "art style description for illustrations",
  "locations": {
    "location_name": "visual description of this location"
  }
}
"""


def generate_story(
    prompt: str,
    age_group: str = "kids",
    client: Optional[QwenClient] = None,
    output_dir: str = "stories",
) -> Story:
    """Generate a complete story from a user prompt.

    Args:
        prompt: The user's story idea (1-3 sentences).
        age_group: "kids" (3-5, 6-8, 9-12) or "adult".
        client: QwenClient instance (creates one if not provided).
        output_dir: Directory to save output files.

    Returns:
        A Story object with scenes and character bible populated.
    """
    if client is None:
        client = QwenClient()

    system = SYSTEM_PROMPT_KIDS if age_group == "kids" else SYSTEM_PROMPT_ADULT
    age_detail = _age_detail(age_group)

    # Honor the user's own opening when they supply one (e.g. "Once upon a time...").
    # Framing the prompt as "User's idea" invites the model to paraphrase instead
    # of following it — so explicitly require the opening phrase to be kept.
    opening_rule = ""
    stripped = prompt.strip()
    if stripped.lower().startswith("once upon a time"):
        opening_rule = (
            "\n\nThe user's idea starts with \"Once upon a time\". "
            "Begin the first scene's narration with that exact phrase, "
            "then continue the story in the same fairy-tale style."
        )

    full_prompt = (
        f"Write a story for {age_detail}.\n\n"
        f"User's idea: {prompt}\n\n"
        f"Generate the story in JSON format.{opening_rule}"
    )

    logger.info("Generating story for prompt: %s", prompt[:80])

    raw_json = None
    data = {}
    scenes_data = None
    last_error = None
    for attempt in range(1, 4):  # up to 3 attempts to get a non-empty story
        raw_json = client.chat_json(
            prompt=full_prompt,
            system=system,
            temperature=0.8,
        )
        data = _parse_json(raw_json)
        scenes_data = data.get("scenes", [])

        # Validate: each scene must actually carry narration text. A model may
        # emit a skeleton (titles only, or alternate field names) which would
        # silently starve image + TTS generation. Retry if any scene lacks text.
        text_counts = [len(str(s.get("text", "") or s.get("narrative", ""))) for s in scenes_data]
        if scenes_data and all(c == 0 for c in text_counts):
            last_error = (
                "Model returned scenes with no narration text (field mismatch "
                "or empty output). Retrying..."
            )
            logger.warning("Attempt %d/3: %s", attempt, last_error)
            continue
        break

    if not scenes_data or all(c == 0 for c in text_counts):
        raise RuntimeError(
            "Story generation failed after 3 attempts: model returned no usable "
            "scene text. Last response snippet: %s" % (raw_json or "")[:300]
        )

    # Build story
    bible = CharacterBible(
        visual_style=data.get("visual_style", "children's book illustration, soft watercolor, warm colors"),
        locations=data.get("locations", {}),
    )

    for char_data in data.get("characters", []):
        if not isinstance(char_data, dict):
            continue
        bible.add_character(Character(
            name=char_data.get("name", ""),
            age=char_data.get("age", ""),
            role=char_data.get("role", "protagonist"),
            appearance=char_data.get("appearance", ""),
            personality=char_data.get("personality", ""),
            notes=char_data.get("notes", ""),
        ))

    scenes = []
    for i, sc_data in enumerate(data.get("scenes", [])):
        if not isinstance(sc_data, dict):
            continue
        scenes.append(Scene(
            index=sc_data.get("index", sc_data.get("number", i + 1)),
            title=sc_data.get("title", f"Scene {i + 1}"),
            text=sc_data.get("text", sc_data.get("narrative", "")),
            description=sc_data.get("description", sc_data.get("scene_description", "")),
            location=sc_data.get("location", sc_data.get("setting", "")),
            characters=sc_data.get("characters", []),
            mood=sc_data.get("mood", "neutral"),
        ))

    story = Story(
        title=data.get("title", prompt[:40]),
        prompt=prompt,
        age_group=age_group,
        bible=bible,
        scenes=scenes,
    )

    # Save outputs
    slug = story.slug
    story_dir = os.path.join(output_dir, slug)
    os.makedirs(story_dir, exist_ok=True)

    # Story JSON
    story_path = os.path.join(story_dir, f"{slug}_story.json")
    with open(story_path, "w", encoding="utf-8") as f:
        f.write(story.to_json())
    logger.info("Story saved to %s", story_path)

    # Bible markdown
    bible_path = os.path.join(story_dir, f"{slug}_bible.md")
    _write_bible_md(bible, story_path, bible_path)
    logger.info("Bible saved to %s", bible_path)

    # Scenes JSON (for legacy compatibility with existing skills)
    scenes_path = os.path.join(story_dir, f"{slug}_scenes.json")
    scenes_data = [s.to_dict() for s in scenes]
    with open(scenes_path, "w", encoding="utf-8") as f:
        json.dump(scenes_data, f, indent=2, ensure_ascii=False)

    return story


def _age_detail(age_group: str) -> str:
    """Map age group to prompt detail."""
    mapping = {
        "kids-3-5": "children aged 3-5 (very simple, short sentences, lots of wonder)",
        "kids-6-8": "children aged 6-8 (engaging, slightly complex, teaches a value)",
        "kids-9-12": "children aged 9-12 (adventurous, creative, growing vocabulary)",
        "kids": "children",
        "kids_older": "children aged 9-12 (adventurous, creative, growing vocabulary)",
        "adult": "adults (any genre, can be complex)",
    }
    return mapping.get(age_group, "children")


def _parse_json(raw: str) -> dict:
    """Extract JSON object from model response, handling markdown fences."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def _write_bible_md(bible: CharacterBible, story_path: str, bible_path: str) -> None:
    """Write a human-readable character bible markdown file."""
    with open(bible_path, "w", encoding="utf-8") as f:
        f.write("# Character Bible\n\n")
        f.write(f"**Visual Style:** {bible.visual_style}\n\n")
        f.write("## Characters\n\n")
        for char in bible.characters.values():
            f.write(f"### {char.name}\n")
            f.write(f"- **Age:** {char.age}\n")
            f.write(f"- **Role:** {char.role}\n")
            f.write(f"- **Appearance:** {char.appearance}\n")
            f.write(f"- **Personality:** {char.personality}\n")
            f.write(f"- **Notes:** {char.notes}\n\n")
        f.write("## Locations\n\n")
        for loc, desc in bible.locations.items():
            f.write(f"### {loc}\n{desc}\n\n")

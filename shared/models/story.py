"""Data models for the story pipeline — Story, Scene, Character, Bible."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Character:
    """A character in the story."""

    name: str
    age: str = ""
    role: str = "protagonist"
    appearance: str = ""  # full visual description
    personality: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Character:
        return cls(**d)


@dataclass
class Scene:
    """A single scene — one illustration + one narration clip."""

    index: int
    title: str = ""
    text: str = ""  # narration text
    description: str = ""  # illustration prompt description (visual only)
    location: str = ""
    characters: list[str] = field(default_factory=list)
    mood: str = "neutral"
    continuity_class: str = "HARD_CUT"  # HARD_CUT | SOFT_CUT | STATE_RESET
    state_changes: dict = field(default_factory=dict)  # e.g. {"fox": "wearing_hat"}

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Scene:
        return cls(**d)


@dataclass
class CharacterBible:
    """The visual bible — detailed character/location appearance specs."""

    characters: dict[str, Character] = field(default_factory=dict)
    locations: dict[str, str] = field(default_factory=dict)
    visual_style: str = "children's book illustration, soft watercolor, warm colors"

    def get_character(self, name: str) -> Optional[Character]:
        return self.characters.get(name)

    def add_character(self, character: Character) -> None:
        self.characters[character.name] = character

    def to_dict(self) -> dict:
        return {
            "characters": {k: v.to_dict() for k, v in self.characters.items()},
            "locations": self.locations,
            "visual_style": self.visual_style,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CharacterBible:
        chars = {}
        for name, cdata in d.get("characters", {}).items():
            chars[name] = Character.from_dict(cdata)
        return cls(
            characters=chars,
            locations=d.get("locations", {}),
            visual_style=d.get("visual_style", "children's book illustration, soft watercolor, warm colors"),
        )


@dataclass
class Story:
    """A complete generated story with scenes and character bible."""

    title: str
    prompt: str = ""  # original user prompt
    age_group: str = "kids"  # kids | adult
    bible: CharacterBible = field(default_factory=CharacterBible)
    scenes: list[Scene] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "prompt": self.prompt,
            "age_group": self.age_group,
            "bible": self.bible.to_dict(),
            "scenes": [s.to_dict() for s in self.scenes],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Story:
        bible = CharacterBible.from_dict(d.get("bible", {}))
        scenes = [Scene.from_dict(s) for s in d.get("scenes", [])]
        return cls(
            title=d["title"],
            prompt=d.get("prompt", ""),
            age_group=d.get("age_group", "kids"),
            bible=bible,
            scenes=scenes,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, data: str) -> Story:
        return cls.from_dict(json.loads(data))

    @property
    def slug(self) -> str:
        """URL-safe identifier derived from title."""
        return self.title.lower().replace(" ", "-")[:50]

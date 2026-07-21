"""Image record for tracking generation metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ImageRecord:
    """Metadata for one generated image."""

    scene_index: int
    prompt: str = ""
    image_url: str = ""
    local_path: str = ""
    seed: int = 0
    character_name: str = ""
    image_type: str = "scene"  # reference | scene
    validation_status: str = "pending"  # pending | passed | failed
    width: int = 1024
    height: int = 1024

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ImageRecord:
        return cls(**d)


class ImageRegistry:
    """Manages all images for one story."""

    def __init__(self):
        self.images: list[ImageRecord] = []

    def add(self, record: ImageRecord) -> None:
        self.images.append(record)

    def by_scene(self, index: int) -> list[ImageRecord]:
        return [img for img in self.images if img.scene_index == index]

    def by_type(self, image_type: str) -> list[ImageRecord]:
        return [img for img in self.images if img.image_type == image_type]

    def references(self) -> list[ImageRecord]:
        return self.by_type("reference")

    def scene_images(self) -> list[ImageRecord]:
        return self.by_type("scene")

    def to_dict(self) -> dict:
        return {"images": [img.to_dict() for img in self.images]}

    @classmethod
    def from_dict(cls, d: dict) -> ImageRegistry:
        reg = cls()
        reg.images = [ImageRecord.from_dict(i) for i in d.get("images", [])]
        return reg

    def save(self, path: str, slug: str) -> str:
        """Save to ``{path}/{slug}_images.json``."""
        import os
        os.makedirs(path, exist_ok=True)
        filepath = os.path.join(path, f"{slug}_images.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return filepath

    @classmethod
    def load(cls, path: str, slug: str) -> ImageRegistry:
        """Load from ``{path}/{slug}_images.json``."""
        import os
        filepath = os.path.join(path, f"{slug}_images.json")
        if not os.path.exists(filepath):
            return cls()
        with open(filepath, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

"""Manages character and location reference images.

Generates reference images (neutral pose, plain bg) per character/location,
then uses them as visual anchors for scene image generation.
"""

import os
import base64
import hashlib
import logging
from typing import Optional

from agent_orchestrator.qwen_client import QwenClient
from shared.models.story import CharacterBible
from image_generation.image_registry import ImageRecord, ImageRegistry
from image_generation.character_consistency.prompt_assembler import build_reference_prompt

logger = logging.getLogger(__name__)


class ReferenceManager:
    """Generates and manages reference images for character consistency."""

    def __init__(self, client: QwenClient, output_dir: str, slug: str):
        self.client = client
        self.output_dir = output_dir
        self.slug = slug
        self.registry = ImageRegistry()

    def generate_character_refs(self, bible: CharacterBible) -> ImageRegistry:
        """Generate one reference image per character.

        Args:
            bible: The character bible.

        Returns:
            ImageRegistry with all reference images.
        """
        for name, char in bible.characters.items():
            if not char.appearance:
                logger.warning("No appearance for %s, skipping ref", name)
                continue

            prompt = build_reference_prompt(name, char.appearance, bible.visual_style)

            logger.info("Generating reference for %s", name)

            results = self.client.generate_image(
                prompt=prompt,
            )

            if results:
                img_url = results[0].get("url", "")
                local_path = self._save_image(img_url, f"ref_{name.lower().replace(' ', '_')}.png")

                record = ImageRecord(
                    scene_index=0,
                    prompt=prompt,
                    image_url=img_url,
                    local_path=local_path,
                    seed=0,
                    character_name=name,
                    image_type="reference",
                    validation_status="pending",
                )
                self.registry.add(record)
                logger.info("Saved reference for %s", name)

        self.registry.save(self.output_dir, self.slug)
        return self.registry

    def get_reference_images(self, character_names: list[str]) -> list[dict]:
        """Get base64-encoded reference images for the given characters.

        Returns:
            List of dicts with keys: character_name, b64_data, seed.
        """
        refs = []
        for img in self.registry.references():
            if img.character_name in character_names and img.local_path:
                with open(img.local_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                refs.append({
                    "character_name": img.character_name,
                    "b64_data": f"data:image/png;base64,{b64}",
                    "seed": img.seed,
                })
        return refs

    def _name_seed(self, name: str) -> int:
        """Deterministic seed from character name."""
        h = hashlib.md5(name.encode()).hexdigest()[:8]
        return int(h, 16) % (2**31)

    def _save_image(self, url: str, filename: str) -> str:
        """Download and save an image from URL with retries."""
        import requests
        import time as _tm

        local_path = os.path.join(self.output_dir, filename)
        last_error = None
        for attempt in range(1, 4):
            try:
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(resp.content)
                return local_path
            except Exception as exc:
                last_error = exc
                logger.warning("Download attempt %d/3 failed: %s", attempt, exc)
                if attempt < 3:
                    _tm.sleep(5.0 * attempt)
        raise RuntimeError(f"Failed to download image after 3 retries: {last_error}")

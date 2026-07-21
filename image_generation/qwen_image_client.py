"""Phase 2-3: Generate character reference images and scene images via Qwen Image 2.0 Pro."""

import os
import logging
from typing import Optional

from agent_orchestrator.qwen_client import QwenClient
from shared.models.story import Story
from image_generation.image_registry import ImageRecord, ImageRegistry
from image_generation.character_consistency.reference_manager import ReferenceManager
from image_generation.character_consistency.prompt_assembler import build_scene_prompt
from image_generation.character_consistency.continuity_classifier import classify_continuity

logger = logging.getLogger(__name__)


def generate_references(
    story: Story,
    client: Optional[QwenClient] = None,
) -> ImageRegistry:
    """Generate character and location reference images.

    Args:
        story: The Story with character bible populated.
        client: QwenClient instance.

    Returns:
        ImageRegistry with reference images.
    """
    if client is None:
        client = QwenClient()

    slug = story.slug
    output_dir = os.path.join("stories", slug)
    os.makedirs(output_dir, exist_ok=True)

    ref_manager = ReferenceManager(client, output_dir, slug)
    registry = ref_manager.generate_character_refs(story.bible)
    return registry


def generate_scene_images(
    story: Story,
    ref_manager: Optional[ReferenceManager] = None,
    client: Optional[QwenClient] = None,
) -> ImageRegistry:
    """Generate one image per scene with character consistency.

    Args:
        story: The Story with scenes and bible.
        ref_manager: ReferenceManager (created if not provided).
        client: QwenClient (created if not provided).

    Returns:
        ImageRegistry with scene images.
    """
    if client is None:
        client = QwenClient()

    slug = story.slug
    output_dir = os.path.join("stories", slug)
    os.makedirs(output_dir, exist_ok=True)

    if ref_manager is None:
        ref_manager = ReferenceManager(client, output_dir, slug)
        ref_manager.registry = ImageRegistry.load(output_dir, slug)

    registry = ImageRegistry()
    registry.images = list(ref_manager.registry.scene_images())

    previous_scene = None

    for scene in story.scenes:
        existing = [img for img in registry.images if img.scene_index == scene.index]
        if existing:
            logger.info("Scene %d image exists, skipping", scene.index)
            previous_scene = scene
            continue

        continuity = classify_continuity(scene, previous_scene)
        scene.continuity_class = continuity

        prompt = build_scene_prompt(scene, story.bible)
        char_refs = ref_manager.get_reference_images(scene.characters)
        seed = 100 + scene.index

        logger.info(
            "Generating scene %d/%d (%s) — %s",
            scene.index, len(story.scenes), scene.title, continuity,
        )

        try:
            # Workspace multimodal endpoint rejects reference images with text.
            # Scene prompts already embed character visual descriptions from the
            # bible via build_scene_prompt.
            results = client.generate_image(
                prompt=prompt,
            )

            if results:
                img_url = results[0].get("url", "")
                local_path = _save_scene_image(img_url, output_dir, slug, scene.index)

                record = ImageRecord(
                    scene_index=scene.index,
                    prompt=prompt,
                    image_url=img_url,
                    local_path=local_path,
                    seed=seed,
                    character_name=", ".join(scene.characters),
                    image_type="scene",
                    validation_status="passed" if local_path else "failed",
                )
                registry.add(record)
                logger.info("Scene %d image saved", scene.index)
        except Exception as exc:
            logger.error("Scene %d image failed: %s", scene.index, exc)

        previous_scene = scene

    registry.save(output_dir, slug)
    return registry


def _save_scene_image(url: str, output_dir: str, slug: str, index: int) -> str:
    """Download and save a scene image from URL with retries.

    The OSS download URLs are valid for 24h but can have transient
    DNS / connectivity issues from this environment.
    """
    import requests
    import time as _tm

    filename = f"{slug}_scene_{index:02d}.png"
    local_path = os.path.join(output_dir, filename)

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
            logger.warning("Download attempt %d/3 for scene %d failed: %s", attempt, index, exc)
            if attempt < 3:
                _tm.sleep(5.0 * attempt)

    logger.error("Failed to download scene %d after 3 retries: %s", index, last_error)
    return ""

"""Export manager — coordinates HTML, PDF, and EPUB export formats."""

import os
import logging
from typing import Optional

from shared.models.story import Story
from image_generation.image_registry import ImageRegistry
from export_pipeline.html_exporter import export_html
from export_pipeline.pdf_exporter import export_pdf
from export_pipeline.epub_exporter import export_epub

logger = logging.getLogger(__name__)


def export_all(
    story: Story,
    images_registry: Optional[ImageRegistry] = None,
    audio_files: Optional[dict[int, str]] = None,
    output_dir: str = "",
    formats: Optional[list[str]] = None,
) -> dict[str, str]:
    """Export a storybook in all requested formats.

    Args:
        story: The Story object.
        images_registry: ImageRegistry with scene images.
        audio_files: Dict mapping scene index to MP3 path.
        output_dir: Output directory (default stories/{slug}).
        formats: List of formats. Defaults to ["html", "pdf", "epub"].

    Returns:
        Dict mapping format name to output file path.
    """
    slug = story.slug
    output_dir = output_dir or os.path.join("stories", slug)
    formats = formats or ["html", "pdf", "epub"]
    os.makedirs(output_dir, exist_ok=True)

    if images_registry is None:
        images_registry = ImageRegistry.load(output_dir, slug)

    results: dict[str, str] = {}

    for fmt in formats:
        fmt = fmt.lower().strip()
        try:
            if fmt == "html":
                path = export_html(story=story, images_registry=images_registry, audio_files=audio_files, output_path=os.path.join(output_dir, f"{slug}.html"))
            elif fmt == "pdf":
                path = export_pdf(story=story, images_registry=images_registry, audio_files=audio_files, output_path=os.path.join(output_dir, f"{slug}.pdf"))
            elif fmt == "epub":
                path = export_epub(story=story, images_registry=images_registry, output_path=os.path.join(output_dir, f"{slug}.epub"))
            else:
                logger.warning("Unknown export format: %s", fmt)
                continue

            results[fmt] = path or ""
            if path:
                logger.info("Exported %s: %s", fmt.upper(), path)
            else:
                logger.warning("Export %s returned empty path", fmt.upper())
        except Exception as exc:
            results[fmt] = ""
            logger.error("Export %s failed: %s", fmt.upper(), exc)

    return results
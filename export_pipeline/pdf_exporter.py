"""PDF exporter — converts the HTML storybook to a printable PDF via weasyprint."""

import os
import logging
from typing import Optional

from shared.models.story import Story
from export_pipeline.html_exporter import export_html

logger = logging.getLogger(__name__)


def export_pdf(
    story: Story,
    images_registry=None,
    audio_files: Optional[dict[int, str]] = None,
    output_path: str = "",
    page_size: str = "A4",
) -> str:
    """Export a storybook as a printable PDF.

    First generates the HTML, then converts to PDF using weasyprint.

    Args:
        story: The Story object.
        images_registry: ImageRegistry with scene images.
        audio_files: Dict mapping scene index to MP3 file path.
        output_path: Where to save the PDF. Defaults to {slug}.pdf.
        page_size: Page size string for weasyprint (default A4).

    Returns:
        Path to the generated PDF file, or empty string on failure.
    """
    slug = story.slug
    story_dir = os.path.join("stories", slug)

    if not output_path:
        output_path = os.path.join(story_dir, f"{slug}.pdf")

    html_path = os.path.join(story_dir, f"{slug}_print.html")
    try:
        export_html(
            story=story,
            images_registry=images_registry,
            audio_files=audio_files,
            output_path=html_path,
        )
    except Exception as exc:
        logger.error("HTML generation for PDF failed: %s", exc)
        return ""

    try:
        from weasyprint import HTML as WeasyprintHTML

        WeasyprintHTML(filename=html_path).write_pdf(
            output_path,
            presentational_hints=True,
        )

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(
                "PDF exported to %s (%d bytes)",
                output_path, os.path.getsize(output_path),
            )
            if os.path.exists(html_path):
                os.remove(html_path)
            return output_path
        else:
            logger.error("PDF output is empty or missing: %s", output_path)
            return ""
    except ImportError:
        logger.warning("weasyprint not installed. Install with: pip install weasyprint")
        return ""
    except Exception as exc:
        logger.error("PDF conversion failed: %s", exc)
        return ""
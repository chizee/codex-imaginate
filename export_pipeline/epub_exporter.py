"""EPUB exporter — creates a Kindle/Apple Books compatible ebook from a story."""

import os
import logging
from typing import Optional

from shared.models.story import Story
from image_generation.image_registry import ImageRegistry

logger = logging.getLogger(__name__)


def export_epub(
    story: Story,
    images_registry: Optional[ImageRegistry] = None,
    output_path: str = "",
) -> str:
    """Export a storybook as an EPUB ebook.

    Uses ebooklib to create a valid EPUB3 file with cover image,
    chapter-per-scene navigation, and embedded illustrations.

    Args:
        story: The Story object.
        images_registry: ImageRegistry with scene images.
        output_path: Where to save the EPUB. Defaults to {slug}.epub.

    Returns:
        Path to the generated EPUB file, or empty string on failure.
    """
    slug = story.slug
    story_dir = os.path.join("stories", slug)

    if not output_path:
        output_path = os.path.join(story_dir, f"{slug}.epub")

    if images_registry is None:
        images_registry = ImageRegistry.load(story_dir, slug)

    try:
        from ebooklib import epub
    except ImportError:
        logger.warning("ebooklib not installed. Install with: pip install ebooklib")
        return ""

    try:
        book = epub.EpubBook()

        book.set_identifier(f"imaginate-{slug}")
        book.set_title(story.title)
        book.set_language("en")
        book.add_author("Imaginate")

        # Cover image
        cover_img = None
        scene_imgs = images_registry.scene_images()
        for img in scene_imgs:
            if img.local_path and os.path.exists(img.local_path) and cover_img is None:
                cover_img = img
        if cover_img and os.path.exists(cover_img.local_path):
            with open(cover_img.local_path, "rb") as f:
                book.set_cover("cover.png", f.read())

        # Add scene images as EPUB resources
        image_items = {}
        for img_record in scene_imgs:
            if img_record.local_path and os.path.exists(img_record.local_path):
                ext = os.path.splitext(img_record.local_path)[1].lower()
                mime = "image/png" if ext == ".png" else "image/jpeg"
                img_item = epub.EpubImage()
                img_item.file_name = f"images/scene_{img_record.scene_index:02d}{ext}"
                img_item.media_type = mime
                with open(img_record.local_path, "rb") as f:
                    img_item.content = f.read()
                book.add_item(img_item)
                image_items[img_record.scene_index] = img_item

        # Chapters (one per scene)
        chapters = []
        toc_items = []

        for scene in story.scenes:
            chapter = epub.EpubHtml(
                title=scene.title or f"Scene {scene.index}",
                file_name=f"scene_{scene.index:02d}.xhtml",
                lang="en",
            )
            img_html = ""
            img_item = image_items.get(scene.index)
            if img_item:
                img_html = f'<div class="scene-image"><img src="{img_item.file_name}" alt="Scene {scene.index}" style="max-width:100%;height:auto;"/></div>'

            chapter.content = f"""<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{scene.title}</title></head>
<body>
  <div class="scene">
    <h2>{scene.title}</h2>
    {img_html}
    <p class="story-text">{scene.text}</p>
  </div>
</body>
</html>"""

            book.add_item(chapter)
            chapters.append(chapter)
            toc_items.append(epub.Link(
                chapter.file_name, scene.title or f"Scene {scene.index}", f"scene_{scene.index}"
            ))

        book.toc = toc_items
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav"] + chapters

        style = """
        body { font-family: Georgia, serif; margin: 1em; }
        .scene { margin-bottom: 2em; }
        h2 { color: #c47a1a; font-size: 1.4em; }
        .scene-image { text-align: center; margin: 1em 0; }
        .story-text { font-size: 1em; line-height: 1.6; }
        """
        css = epub.EpubItem(
            uid="style", file_name="style/default.css", media_type="text/css", content=style,
        )
        book.add_item(css)
        for chapter in chapters:
            chapter.add_item(css)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        epub.write_epub(output_path, book, {})

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info("EPUB exported to %s (%d bytes)", output_path, os.path.getsize(output_path))
            return output_path
        else:
            logger.error("EPUB output is empty or missing: %s", output_path)
            return ""

    except Exception as exc:
        logger.error("EPUB export failed: %s", exc)
        return ""
"""PDF exporter — generates a print-friendly HTML then converts to PDF via WeasyPrint."""

import os
import base64
import logging
from io import BytesIO
from typing import Optional

from PIL import Image

from shared.models.story import Story

logger = logging.getLogger(__name__)

AUDIO_BASE_URL = "https://imaginate.omenabyte.com"


def _compress_image(filepath: str) -> str:
    """Resize (max 1024px) and compress image, return base64 JPEG."""
    try:
        img = Image.open(filepath)
        # Resize if too big
        max_dim = 1024
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buf = BytesIO()
        # Convert RGBA/P to RGB for JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as exc:
        logger.warning("Image compression failed for %s: %s", filepath, exc)
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


PDF_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Georgia', 'Times New Roman', serif; color: #222; background: #fff; }
.page {
  page-break-after: always;
  padding: 40px 50px 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}
.page img {
  max-width: 100%;
  max-height: 65vh;
  height: auto;
  object-fit: contain;
  border-radius: 6px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}
.page .text {
  margin-top: 24px;
  font-size: 16px;
  line-height: 1.7;
  color: #333;
  text-align: center;
  max-width: 90%;
}
.page .scene-num {
  margin-top: 12px;
  color: #999;
  font-size: 12px;
  text-align: center;
}
.page .audio-link {
  margin-top: 16px;
  font-size: 14px;
}
.page .audio-link a {
  color: #c47a1a;
  text-decoration: none;
  border: 1px solid #c47a1a;
  padding: 6px 14px;
  border-radius: 20px;
  display: inline-block;
}
.page .placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80%;
  height: 200px;
  background: #f0ebe3;
  border-radius: 8px;
  color: #aaa;
  font-size: 13px;
  font-style: italic;
}
.cover-page {
  justify-content: center;
  text-align: center;
  background: linear-gradient(135deg, #fdf8f0 0%, #f5ede2 100%);
}
.cover-page h1 {
  font-size: 28px;
  color: #8b5e3c;
  margin-bottom: 12px;
}
.cover-page .subtitle {
  font-size: 16px;
  color: #b08660;
}
.footer {
  text-align: center;
  padding: 10px 0;
  font-size: 11px;
  color: #bbb;
}
"""


def export_pdf(
    story: Story,
    images_registry=None,
    audio_files: Optional[dict[int, str]] = None,
    output_path: str = "",
) -> str:
    """Export a storybook as a printable PDF.

    Generates a print-friendly static HTML (no JS), then converts to PDF
    using WeasyPrint. Audio narration is embedded as hyperlinks to the
    hosted audio files (PDFs cannot play audio in browser viewers).

    Args:
        story: The Story object.
        images_registry: ImageRegistry with scene images.
        audio_files: Dict mapping scene index (1-based) to audio file path.
        output_path: Where to save the PDF.

    Returns:
        Path to the generated PDF file, or empty string on failure.
    """
    slug = story.slug
    story_dir = os.path.join("stories", slug)

    if not output_path:
        output_path = os.path.join(story_dir, f"{slug}.pdf")

    if not story.scenes:
        logger.error("No scenes to export")
        return ""

    try:
        from weasyprint import HTML as WeasyprintHTML
    except ImportError:
        logger.warning("weasyprint not installed. Install with: pip install weasyprint")
        return ""

    # ── Build a print-friendly HTML ──
    pages_html = []

    # Cover page
    age = story.age_group or "Children"
    pages_html.append(f"""<div class="page cover-page">
  <h1>{story.title}</h1>
  <p class="subtitle">{age} · {len(story.scenes)} Scenes</p>
</div>""")

    for i, scene in enumerate(story.scenes, start=1):
        parts = []

        # Image
        if images_registry:
            imgs = images_registry.by_scene(i)
            if imgs:
                b64 = _compress_image(imgs[0].local_path)
                parts.append(f'<img src="data:image/jpeg;base64,{b64}" alt="Scene {i}">')
            else:
                parts.append('<div class="placeholder">Illustration unavailable</div>')
        else:
            parts.append('<div class="placeholder">Illustration unavailable</div>')

        # Text
        text = scene.text or scene.description or ""
        parts.append(f'<div class="text">{text}</div>')

        # Scene number
        parts.append(f'<div class="scene-num">{i}/{len(story.scenes)}</div>')

        # Audio link (hosted)
        if audio_files and i in audio_files:
            audio_path = audio_files[i]
            audio_filename = os.path.basename(audio_path)
            audio_url = f"{AUDIO_BASE_URL}/stories/{slug}/{slug}_audio/{audio_filename}"
            parts.append(f'<div class="audio-link">🎵 <a href="{audio_url}" target="_blank">Listen to narration</a></div>')
        else:
            parts.append('')

        pages_html.append('<div class="page">\n' + "\n".join(parts) + "\n</div>")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{story.title} — Imaginate (PDF)</title>
<style>{PDF_CSS}</style>
</head>
<body>
{''.join(pages_html)}
<div class="footer">Generated by Imaginate AI · Powered by Qwen Cloud</div>
</body>
</html>"""

    # ── Write intermediate HTML and convert to PDF ──
    tmp_html = os.path.join(story_dir, f"{slug}_print.html")
    try:
        with open(tmp_html, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("Print HTML written to %s (%d chars)", tmp_html, len(html_content))
    except Exception as exc:
        logger.error("Failed to write print HTML: %s", exc)
        return ""

    try:
        WeasyprintHTML(filename=tmp_html).write_pdf(
            output_path,
            presentational_hints=True,
        )

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(
                "PDF exported to %s (%d bytes)",
                output_path, os.path.getsize(output_path),
            )
            if os.path.exists(tmp_html):
                os.remove(tmp_html)
            return output_path
        else:
            logger.error("PDF output is empty or missing: %s", output_path)
            return ""
    except Exception as exc:
        logger.error("PDF conversion failed: %s", exc)
        # Keep tmp_html for debugging
        return ""

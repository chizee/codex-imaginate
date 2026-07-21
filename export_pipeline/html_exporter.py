"""Phase 6: Self-contained HTML storybook with embedded images and audio."""

import os
import base64
import json
import logging
from typing import Optional

from shared.models.story import Story
from image_generation.image_registry import ImageRegistry

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>{title} — Imaginate</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Georgia', serif; background: #f5f0e8; overflow: hidden; height: 100vh; }}
  #book {{ display: flex; overflow-x: auto; scroll-snap-type: x mandatory; height: 100vh; }}
  .page {{ min-width: 100vw; height: 100vh; scroll-snap-align: start; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; position: relative; }}
  .page img {{ max-width: 90vw; max-height: 60vh; object-fit: contain; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); }}
  .page .text {{ max-width: 80vw; margin-top: 20px; font-size: 18px; line-height: 1.6; color: #333; text-align: center; }}
  .page .scene-num {{ position: absolute; bottom: 20px; right: 20px; color: #999; font-size: 14px; }}
  .page .audio-btn {{ position: absolute; bottom: 20px; left: 20px; width: 40px; height: 40px; border-radius: 50%; border: 2px solid #c47a1a; background: white; color: #c47a1a; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; }}
  .page .audio-btn:hover {{ background: #c47a1a; color: white; }}
  #nav {{ position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); display: flex; gap: 10px; z-index: 10; }}
  #nav button {{ width: 12px; height: 12px; border-radius: 50%; border: 2px solid #c47a1a; background: transparent; cursor: pointer; }}
  #nav button.active {{ background: #c47a1a; }}
  #controls {{ position: fixed; top: 20px; right: 20px; z-index: 10; display: flex; gap: 8px; }}
  #controls button {{ padding: 8px 16px; border: none; border-radius: 4px; background: #c47a1a; color: white; cursor: pointer; font-size: 14px; }}
  #controls button:hover {{ background: #a0600a; }}
  @media (max-width: 600px) {{ .page .text {{ font-size: 16px; }} .page img {{ max-height: 50vh; }} }}
</style>
</head>
<body>
<div id="controls">
  <button onclick="document.getElementById('book').scrollTo({{left:0,behavior:'smooth'}})">⏮ Cover</button>
  <button onclick="toggleAutoPlay()">▶ Auto</button>
</div>
<div id="book">
{pages}
</div>
<div id="nav">
{dots}
</div>
<script>
  const book = document.getElementById('book');
  const dots = document.querySelectorAll('#nav button');
  const audios = document.querySelectorAll('audio');
  let autoPlaying = false;
  let autoTimer = null;

  book.addEventListener('scroll', () => {{
    const idx = Math.round(book.scrollLeft / book.clientWidth);
    dots.forEach((d, i) => d.classList.toggle('active', i === idx));
    audios.forEach(a => a.pause());
    const current = audios[idx];
    if (current) {{ current.currentTime = 0; current.play().catch(() => {{}}); }}
  }});

  function toggleAutoPlay() {{
    autoPlaying = !autoPlaying;
    if (autoPlaying) {{
      autoTimer = setInterval(() => {{
        const idx = Math.round(book.scrollLeft / book.clientWidth);
        if (idx < audios.length - 1) book.scrollTo({{left: (idx+1)*book.clientWidth, behavior:'smooth'}});
        else {{ clearInterval(autoTimer); autoPlaying = false; }}
      }}, 8000);
    }} else {{ clearInterval(autoTimer); }}
  }}

  let touchStartX = 0;
  book.addEventListener('touchstart', e => touchStartX = e.touches[0].clientX);
  book.addEventListener('touchend', e => {{
    const diff = touchStartX - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 50) {{
      const idx = Math.round(book.scrollLeft / book.clientWidth);
      const target = diff > 0 ? idx + 1 : idx - 1;
      if (target >= 0 && target < audios.length) book.scrollTo({{left: target*book.clientWidth, behavior:'smooth'}});
    }}
  }});
</script>
</body>
</html>"""


PAGE_TEMPLATE = """<div class="page" data-index="{index}">
  <img src="{image_b64}" alt="Scene {index}">
  <div class="text">{text}</div>
  <div class="scene-num">{index}/{total}</div>
  <div class="audio-btn" onclick="document.querySelectorAll('audio')[__AUDIO_IDX__].play()">▶</div>
  <audio src="{audio_b64}" preload="auto"></audio>
</div>"""


def export_html(
    story: Story,
    images_registry: Optional[ImageRegistry] = None,
    audio_files: Optional[dict[int, str]] = None,
    output_path: str = "",
) -> str:
    """Export a self-contained HTML storybook.

    Args:
        story: The Story object.
        images_registry: ImageRegistry with scene images.
        audio_files: Dict mapping scene index to MP3 file path.
        output_path: Where to save the HTML.

    Returns:
        Path to the generated HTML file.
    """
    slug = story.slug
    story_dir = os.path.join("stories", slug)

    if not output_path:
        output_path = os.path.join(story_dir, f"{slug}.html")

    if images_registry is None:
        images_registry = ImageRegistry.load(story_dir, slug)

    if audio_files is None:
        manifest_path = os.path.join(story_dir, f"{slug}_audio", "manifest.json")
        audio_files = {}
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                manifest = json.load(f)
            for k, v in manifest.get("files", {}).items():
                audio_files[int(k)] = v

    pages = []
    dots = []
    total_scenes = len(story.scenes)

    for i, scene in enumerate(story.scenes):
        scene_imgs = images_registry.by_scene(scene.index)
        img_path = scene_imgs[0].local_path if scene_imgs else ""
        img_b64 = _file_to_b64(img_path, "image/png") if img_path and os.path.exists(img_path) else ""

        audio_path = audio_files.get(scene.index, "")
        audio_b64 = _file_to_b64(audio_path, "audio/mpeg") if audio_path and os.path.exists(audio_path) else ""

        page_html = PAGE_TEMPLATE.format(
            index=scene.index,
            image_b64=img_b64,
            text=scene.text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>"),
            total=total_scenes,
            audio_b64=audio_b64,
            __AUDIO_IDX__=i,
        )
        pages.append(page_html)
        dots.append(f'<button onclick="book.scrollTo({{left:{i}*book.clientWidth,behavior:\'smooth\'}})" class="{'active' if i==0 else ''}"></button>')

    html = HTML_TEMPLATE.format(
        title=story.title.replace("<", "&lt;").replace(">", "&gt;"),
        pages="\n".join(pages),
        dots="\n".join(dots),
    )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("HTML exported to %s", output_path)
    return output_path


def _file_to_b64(filepath: str, mime: str) -> str:
    """Read a file and return a base64 data URI."""
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

"""Phase 6: Self-contained HTML storybook with embedded images and audio.

Rebuilt reader with event-driven autoplay, Previous/Next controls,
keyboard and touch navigation, and robust asset fallback discovery.
"""

import os
import base64
import json
import mimetypes
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
  body {{ font-family: 'Georgia', serif; background: #f5f0e8; overflow: hidden; height: 100vh; user-select: none; }}
  .page {{ display: none; width: 100vw; height: 100vh; flex-direction: column; align-items: center; justify-content: center; padding: 20px; position: relative; }}
  .page.active {{ display: flex; }}
  .page img {{ max-width: 90vw; max-height: 60vh; object-fit: contain; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); }}
  .page .text {{ max-width: 80vw; margin-top: 20px; font-size: 18px; line-height: 1.6; color: #333; text-align: center; }}
  .page .scene-num {{ position: absolute; bottom: 60px; right: 20px; color: #999; font-size: 14px; }}
  .placeholder {{ display: flex; align-items: center; justify-content: center; width: 90vw; height: 40vh; background: #e8ddd0; border-radius: 8px; color: #aaa; font-size: 14px; font-style: italic; }}
  #controls {{ position: fixed; bottom: 0; left: 0; right: 0; display: flex; align-items: center; justify-content: center; gap: 12px; padding: 12px 20px; background: rgba(245,240,232,0.95); border-top: 1px solid #ddd; z-index: 10; }}
  #controls button {{ padding: 8px 18px; border: 1px solid #c47a1a; border-radius: 6px; background: white; color: #c47a1a; cursor: pointer; font-size: 14px; font-family: inherit; transition: all 0.15s; }}
  #controls button:hover {{ background: #c47a1a; color: white; }}
  #controls button:disabled {{ opacity: 0.3; cursor: default; background: white; color: #c47a1a; border-color: #ddd; }}
  #controls .nav-btn {{ min-width: 80px; }}
  #nav-dots {{ display: flex; gap: 8px; }}
  #nav-dots button {{ width: 10px; height: 10px; padding: 0; border-radius: 50%; border: 2px solid #c47a1a; background: transparent; cursor: pointer; min-width: unset; }}
  #nav-dots button.active {{ background: #c47a1a; }}
  @media (max-width: 600px) {{ .page .text {{ font-size: 16px; }} .page img {{ max-height: 50vh; }} }}
</style>
</head>
<body>
<div id="pages">
{pages}
</div>
<div id="controls">
  <button class="nav-btn" id="prev-btn" onclick="goTo(currentPage-1)" disabled>← Previous</button>
  <button onclick="goTo(0)">⏮ Cover</button>
  <div id="nav-dots">{dots}</div>
  <button id="play-btn" onclick="toggleNarrate()">▶ Narrate</button>
  <button id="auto-btn" onclick="toggleAutoPlay()">▶ Autoplay</button>
  <button class="nav-btn" id="next-btn" onclick="goTo(currentPage+1)">Next →</button>
</div>
<script>
  const totalPages = {total};
  let currentPage = 0;
  let autoplay = false;
  let playTimer = null;

  function goTo(idx) {{
    if (idx < 0 || idx >= totalPages) return;
    document.querySelectorAll('.page').forEach((p,i) => p.classList.toggle('active', i===idx));
    document.querySelectorAll('#nav-dots button').forEach((d,i) => d.classList.toggle('active', i===idx));
    document.getElementById('prev-btn').disabled = idx === 0;
    document.getElementById('next-btn').disabled = idx === totalPages - 1;
    currentPage = idx;
    // Pause any playing audio
    document.querySelectorAll('audio').forEach(a => {{ a.pause(); a.currentTime = 0; }});
  }}

  function currentAudio() {{
    return document.querySelectorAll('audio')[currentPage];
  }}

  function toggleNarrate() {{
    const btn = document.getElementById('play-btn');
    const audio = currentAudio();
    if (!audio) {{ btn.textContent = '▶ Narrate'; return; }}
    if (audio.paused) {{
      audio.play().catch(() => {{}});
      btn.textContent = '⏸ Pause';
    }} else {{
      audio.pause();
      btn.textContent = '▶ Narrate';
    }}
  }}

  function toggleAutoPlay() {{
    const btn = document.getElementById('auto-btn');
    autoplay = !autoplay;
    btn.textContent = autoplay ? '⏹ Stop' : '▶ Autoplay';
    if (autoplay) {{
      document.getElementById('play-btn').textContent = '▶ Narrate';
      advanceIfAuto();
    }}
  }}

  function advanceIfAuto() {{
    if (!autoplay) return;
    const audio = currentAudio();
    if (audio && !audio.paused) {{
      // Wait for audio to end
      audio.addEventListener('ended', function handler() {{
        audio.removeEventListener('ended', handler);
        if (autoplay && currentPage < totalPages - 1) goTo(currentPage + 1);
        if (autoplay) setTimeout(advanceIfAuto, 800);
      }});
    }} else {{
      // No audio or already stopped — wait then advance
      if (currentPage < totalPages - 1) {{
        setTimeout(() => {{ if (autoplay) goTo(currentPage + 1); setTimeout(advanceIfAuto, 800); }}, 3000);
      }}
    }}
  }}

  // Audio ended handler for normal playback
  document.querySelectorAll('audio').forEach(a => a.addEventListener('ended', () => {{
    document.getElementById('play-btn').textContent = '▶ Narrate';
    if (autoplay) advanceIfAuto();
  }}));

  // Keyboard controls
  document.addEventListener('keydown', e => {{
    if (e.key === 'ArrowLeft') goTo(currentPage - 1);
    if (e.key === 'ArrowRight') goTo(currentPage + 1);
    if (e.key === ' ') {{ e.preventDefault(); toggleNarrate(); }}
  }});

  // Touch swipe
  let touchStartX = 0;
  document.addEventListener('touchstart', e => touchStartX = e.changedTouches[0].clientX);
  document.addEventListener('touchend', e => {{
    const diff = touchStartX - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 50) goTo(currentPage + (diff > 0 ? 1 : -1));
  }});
</script>
</body>
</html>"""

PAGE_TEMPLATE = """<div class="page" data-index="{index}">
  {image_html}
  <div class="text">{text}</div>
  <div class="scene-num">{index}/{total}</div>
  {audio_html}
</div>"""


def export_html(
    story: Story,
    images_registry: Optional[ImageRegistry] = None,
    audio_files: Optional[dict[int, str]] = None,
    output_path: str = "",
) -> str:
    """Export a self-contained HTML storybook with rebuilt reader controls.

    Args:
        story: The Story object.
        images_registry: ImageRegistry with scene images.
        audio_files: Dict mapping scene index to audio file path.
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
        scene_index = scene.index
        scene_label = _escape_text(scene.title or f"Scene {scene_index}")
        scene_text = _escape_text(scene.text).replace("\n", "<br>")

        # --- Image discovery ---
        img_path = ""
        scene_imgs = images_registry.by_scene(scene_index) if images_registry else []
        if scene_imgs and scene_imgs[0].local_path and os.path.exists(scene_imgs[0].local_path):
            img_path = scene_imgs[0].local_path

        # Fallback: try conventional filename when registry is stale
        if not img_path:
            fallback_png = os.path.join(story_dir, f"{slug}_scene_{scene_index:02d}.png")
            fallback_jpg = os.path.join(story_dir, f"{slug}_scene_{scene_index:02d}.jpg")
            if os.path.exists(fallback_png):
                img_path = fallback_png
            elif os.path.exists(fallback_jpg):
                img_path = fallback_jpg

        if img_path and os.path.exists(img_path):
            mime = _detect_mime(img_path)
            img_b64 = _file_to_b64(img_path, mime)
            image_html = f'<img src="{img_b64}" alt="Scene {scene_index}">'
        else:
            image_html = '<div class="placeholder">Illustration unavailable</div>'

        # --- Audio discovery ---
        audio_path = audio_files.get(scene_index, "") if audio_files else ""
        audio_html = ""

        # Fallback: try conventional filenames when manifest is stale
        if not audio_path or not os.path.exists(audio_path):
            for ext in [".mp3", ".wav"]:
                candidate = os.path.join(story_dir, f"{slug}_audio", f"{slug}_part_{scene_index:02d}{ext}")
                if os.path.exists(candidate):
                    audio_path = candidate
                    break

        if audio_path and os.path.exists(audio_path):
            mime = _detect_mime(audio_path)
            audio_b64 = _file_to_b64(audio_path, mime)
            audio_html = f'<audio src="{audio_b64}" preload="auto"></audio>'

        page_html = PAGE_TEMPLATE.format(
            index=scene_index,
            image_html=image_html,
            text=scene_text,
            total=total_scenes,
            audio_html=audio_html,
        )
        pages.append(page_html)
        active_class = "active" if i == 0 else ""
        dots.append(
            f'<button onclick="goTo({i})" class="{active_class}"></button>'
        )

    html = HTML_TEMPLATE.format(
        title=_escape_text(story.title),
        pages="\n".join(pages),
        dots="\n".join(dots),
        total=total_scenes,
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


def _detect_mime(filepath: str) -> str:
    """Detect MIME type from file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
    }
    return mime_map.get(ext, mimetypes.guess_type(filepath)[0] or "application/octet-stream")


def _escape_text(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;"))

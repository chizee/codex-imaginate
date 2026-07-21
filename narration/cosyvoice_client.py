"""Phase 4: TTS narration via qwen3-tts-instruct-flash.

Uses the multimodal-generation endpoint:
  POST /api/v1/services/aigc/multimodal-generation/generation
Returns audio URL in output.audio.url — download and save as MP3.
"""

import json
import os
import logging
import requests
import subprocess
from typing import Optional

from shared.config.settings import settings
from shared.models.story import Story

logger = logging.getLogger(__name__)

_TTS_URL = f"{settings.QWEN_DASHSCOPE_BASE}/services/aigc/multimodal-generation/generation"


def generate_narration(
    story: Story,
    voice: str = "",
    api_key: str = "",
) -> dict:
    """Generate one MP3 narration per scene via qwen3-tts-instruct-flash.

    Args:
        story: The Story object with scenes.
        voice: Voice name (ignored for qwen3-tts-instruct-flash).
        api_key: DashScope API key.

    Returns:
        Dict mapping scene index (int) to local MP3 file path.
    """
    if not api_key:
        api_key = os.environ.get("DASHSCOPE_API_KEY", "")

    slug = story.slug
    story_dir = os.path.join("stories", slug)
    audio_dir = os.path.join(story_dir, f"{slug}_audio")
    os.makedirs(audio_dir, exist_ok=True)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    results = {}

    for scene in story.scenes:
        if not scene.text.strip():
            logger.warning("Scene %d has no text, skipping", scene.index)
            continue

        filename = f"{slug}_part_{scene.index:02d}.mp3"
        filepath = os.path.join(audio_dir, filename)

        if os.path.exists(filepath):
            logger.info("Scene %d narration exists, skipping", scene.index)
            results[scene.index] = filepath
            continue

        text = scene.text.strip()
        logger.info("Generating TTS for scene %d (%d chars)", scene.index, len(text))

        payload = {
            "model": "qwen3-tts-instruct-flash",
            "input": {
                "text": text,
                "voice": voice,
                "language_type": "English",
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": "Read this story text aloud with expression."}]}
                ],
            },
            "parameters": {
                "format": "wav",
            },
        }

        try:
            resp = requests.post(_TTS_URL, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            audio_url = data.get("output", {}).get("audio", {}).get("url", "")

            if not audio_url:
                logger.error("No audio URL in response for scene %d", scene.index)
                continue

            # Download the WAV audio
            audio_resp = requests.get(audio_url, timeout=60)
            audio_resp.raise_for_status()

            wav_path = filepath.replace(".mp3", ".wav")
            with open(wav_path, "wb") as f:
                f.write(audio_resp.content)
            logger.info("Downloaded WAV for scene %d (%d bytes)", scene.index, len(audio_resp.content))

            # Convert WAV to MP3 using ffmpeg if available
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", filepath],
                    capture_output=True, timeout=30,
                )
                if os.path.exists(filepath):
                    os.remove(wav_path)
                    logger.info("Converted to MP3: %s", filepath)
                else:
                    filepath = wav_path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                filepath = wav_path  # Keep as WAV if ffmpeg not available

            results[scene.index] = filepath

        except Exception as exc:
            logger.error("TTS failed for scene %d: %s", scene.index, exc)

    # Save manifest
    manifest = {
        "slug": slug,
        "files": {str(k): v for k, v in results.items()},
    }
    manifest_path = os.path.join(audio_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return results

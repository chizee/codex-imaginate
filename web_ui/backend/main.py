"""Imaginate — FastAPI backend for the web UI."""

import os
import json
import logging
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from shared.models.story import Story
from agent_orchestrator.orchestrator import run_pipeline
from image_generation.image_registry import ImageRegistry
from export_pipeline.export_manager import export_all
from narration.tts_manager import list_voices

logger = logging.getLogger(__name__)

app = FastAPI(title="Imaginate", version="1.0.0")

# ── Rate limiting (per-IP, tiered) ──
rate_store: dict[str, list[float]] = {}
RATE_LIMITS = {"/api/pipeline": 3, "/api/export": 10}  # max requests per 5 min


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in RATE_LIMITS:
        ip = request.client.host if request.client else "unknown"
        now = datetime.utcnow().timestamp()
        key = f"{ip}:{request.url.path}"
        hits = rate_store.get(key, [])
        hits = [t for t in hits if now - t < 300]
        if len(hits) >= RATE_LIMITS[request.url.path]:
            raise HTTPException(status_code=429, detail="Rate limit exceeded (5 min window)")
        hits.append(now)
        rate_store[key] = hits
    return await call_next(request)


# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir, html=True), name="frontend")

# Serve generated stories (images, audio, HTML, PDF, EPUB)
stories_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "stories")
if not os.path.isdir(stories_dir):
    stories_dir = os.path.join(os.getcwd(), "stories")
if os.path.isdir(stories_dir):
    app.mount("/stories", StaticFiles(directory=stories_dir), name="stories")

@app.get("/")
async def serve_landing():
    from fastapi.responses import HTMLResponse
    landing = os.path.join(frontend_dir, "landing.html")
    if os.path.exists(landing):
        with open(landing, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index):
        with open(index, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return {"error": "frontend not found"}


@app.get("/app")
async def serve_app():
    from fastapi.responses import HTMLResponse
    index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index):
        with open(index, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return {"error": "app not found"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PipelineRequest(BaseModel):
    prompt: str
    age_group: str = "kids"
    voice: str = "ethan"

class ExportRequest(BaseModel):
    slug: str
    formats: list[str] = ["html", "pdf", "epub"]

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/api/voices")
async def voices():
    return {"voices": list_voices()}

@app.get("/api/stories")
async def list_stories():
    stories_dir = "stories"
    if not os.path.isdir(stories_dir):
        return {"stories": []}
    results = []
    for name in sorted(os.listdir(stories_dir), reverse=True):
        story_json = os.path.join(stories_dir, name, f"{name}_story.json")
        if os.path.isfile(story_json):
            try:
                with open(story_json, encoding="utf-8") as f:
                    data = json.load(f)
                    results.append({
                        "slug": name,
                        "title": data.get("title", name),
                        "prompt": data.get("prompt", ""),
                        "scenes": len(data.get("scenes", [])),
                    })
            except Exception:
                pass
    return {"stories": results}

@app.get("/api/stories/{slug}")
async def get_story(slug: str):
    story_dir = os.path.join("stories", slug)
    story_json = os.path.join(story_dir, f"{slug}_story.json")
    if not os.path.isfile(story_json):
        raise HTTPException(status_code=404, detail="Story not found")
    with open(story_json, encoding="utf-8") as f:
        story_data = json.load(f)
    registry = ImageRegistry.load(story_dir, slug)
    manifest_path = os.path.join(story_dir, f"{slug}_audio", "manifest.json")
    audio_manifest = {}
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            audio_manifest = json.load(f)
    return {"story": story_data, "images": registry.to_dict(), "audio": audio_manifest}

@app.post("/api/pipeline")
async def start_pipeline(req: PipelineRequest):
    try:
        html_path = run_pipeline(prompt=req.prompt, age_group=req.age_group, voice=req.voice)
        if not html_path or not os.path.exists(html_path):
            raise HTTPException(status_code=500, detail="HTML not found")
        return {"status": "complete", "html_path": html_path, "slug": os.path.basename(os.path.dirname(html_path))}
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/export")
async def export_story(req: ExportRequest):
    story_dir = os.path.join("stories", req.slug)
    story_json = os.path.join(story_dir, f"{req.slug}_story.json")
    if not os.path.isfile(story_json):
        raise HTTPException(status_code=404, detail="Story not found")
    with open(story_json, encoding="utf-8") as f:
        story = Story.from_json(f.read())
    images_registry = ImageRegistry.load(story_dir, req.slug)
    manifest_path = os.path.join(story_dir, f"{req.slug}_audio", "manifest.json")
    audio_files = {}
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            m = json.load(f)
        audio_files = {int(k): v for k, v in m.get("files", {}).items()}
    results = export_all(story=story, images_registry=images_registry, audio_files=audio_files, formats=req.formats)
    return {"exports": results}

@app.get("/api/exports/{slug}/{format}")
async def download_export(slug: str, format: str):
    story_dir = os.path.join("stories", slug)
    if not os.path.exists(story_dir):
        raise HTTPException(status_code=404, detail="Story not found")

    # Regenerate HTML and PDF with the latest exporter code
    if format in ("html", "pdf"):
        try:
            story_json = os.path.join(story_dir, f"{slug}_story.json")
            if not os.path.isfile(story_json):
                raise HTTPException(status_code=404, detail="Story data not found")
            with open(story_json, encoding="utf-8") as f:
                story = Story.from_json(f.read())
            images_registry = ImageRegistry.load(story_dir, slug)
            audio_files = {}
            manifest_path = os.path.join(story_dir, f"{slug}_audio", "manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path) as f:
                    manifest = json.load(f)
                for k, v in manifest.get("files", {}).items():
                    audio_files[int(k)] = v

            if format == "html":
                from export_pipeline.html_exporter import export_html
                filepath = export_html(story, images_registry, audio_files, os.path.join(story_dir, f"{slug}.html"))
            else:
                from export_pipeline.pdf_exporter import export_pdf
                filepath = export_pdf(story, images_registry, audio_files, os.path.join(story_dir, f"{slug}.pdf"))
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("%s regeneration failed for %s: %s", format, slug, exc)
            filepath = os.path.join(story_dir, f"{slug}.{format}")
            if not os.path.exists(filepath):
                raise HTTPException(status_code=500, detail=f"Failed to regenerate {format} export")
    else:
        filepath = os.path.join(story_dir, f"{slug}.{format}")
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Export not found")

    media_types = {"html": "text/html", "pdf": "application/pdf", "epub": "application/epub+zip"}
    return FileResponse(filepath, media_type=media_types.get(format), filename=f"{slug}.{format}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

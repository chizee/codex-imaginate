# Imaginate ✦

> **One prompt → complete illustrated storybook with narration, multi-format exports**

[![Track](https://img.shields.io/badge/Track-Codex%20Build%20Week-c47a1a)]()
[![Qwen Cloud](https://img.shields.io/badge/Powered%20by-Qwen%20Cloud-2563eb)]()
[![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red)]()

---

## 🏆 Global AI Hackathon Series with Qwen Cloud

**Submission:** July 20, 2026

---

## ✨ What It Does

Imaginate turns **one sentence** into a complete, professional storybook:

1. **Full Script** — Story with scenes, characters, and narrative arc
2. **Character-consistent Illustrations** — Per-character reference images then scene illustrations
3. **Narration Audio** — Natural English TTS (Ethan, Serena, or Cherry)
4. **Multi-format Export** — HTML (interactive), PDF (printable), EPUB (Kindle/Apple Books)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Qwen Cloud API key

### Run the CLI

```bash
pip install openai python-dotenv requests weasyprint ebooklib
echo "DASHSCOPE_API_KEY=sk-your-key" > .env
python -m imaginate "A brave little fox discovers a magical garden" --age kids
```

### Run the Web UI

```bash
pip install fastapi uvicorn
uvicorn web_ui.backend.main:app --port 8000
```

Open `http://localhost:8000`.

---

## 🏗 Architecture

All API calls use **Qwen Cloud exclusively** (zero Claude, Fal, or ElevenLabs).
Deployed on **Alibaba Cloud Function Compute** with API Gateway and OSS.

```
User → FastAPI → Pipeline Orchestrator
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
  Script Gen    Image Gen      TTS
  (qwen3.7-max) (qwen-image-   (qwen3-tts-
                 2.0-pro)      instruct-flash)
       │            │            │
       └────────────┼────────────┘
                    ▼
             Export Pipeline
          HTML | PDF | EPUB
```

---

## 📦 Project Structure

```
imaginate-ai/
├── agent_orchestrator/       # Pipeline orchestration + Qwen client
├── script_generator/         # Story script via qwen3.7-max
├── image_generation/         # Image pipeline + character consistency
├── narration/                # TTS narration + voice manager
├── export_pipeline/          # HTML / PDF / EPUB exporters
├── web_ui/                   # FastAPI backend + premium frontend
├── shared/models/            # Data models (Story, Scene, etc.)
├── alibaba_deploy/           # Dockerfile + FC deployment template
├── docs/                     # Architecture diagram, deployment proof
└── README.md
```

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML/CSS/JS (dark theme, Inter font, premium design) |
| Backend | Python 3.12, FastAPI |
| LLM | Qwen3.7-max |
| Image Gen | Qwen Image 2.0 Pro |
| TTS | Qwen3-tts-instruct-flash |
| PDF | weasyprint |
| EPUB | ebooklib |
| Deployment | Alibaba Cloud FC + API Gateway + OSS |

---

## 🧠 Built with Codex & GPT‑5.6

This project was developed for the **OpenAI Build Week Hackathon** using:

| Tool | Role |
|------|------|
| **Codex CLI** | Initial project scaffolding, FastAPI backend setup, image generation pipeline orchestration, Docker deployment configuration, and API client code |
| **GPT‑5.6** | Story script prompts optimization, export pipeline debugging (PDF/EPUB), TTS API payload refinement, and code review |
| **Codex Session ID** | *(add your session ID from `/feedback`)* |

### How Codex Accelerated Development

1. **Rapid prototyping** — Codex generated the initial FastAPI router, Qwen API integration, and the orchestrator pipeline skeleton from natural language descriptions, cutting setup time from hours to minutes.
2. **Iterative debugging** — During TTS integration, Codex helped diagnose API 400 errors by analyzing the payload format and comparing it against the Qwen Cloud documentation, leading to a fix that would have taken manual trial and error.
3. **Deployment automation** — Codex scaffolded the Dockerfile, docker-compose, and deployment configuration that runs the app on this VPS behind Caddy reverse proxy.
4. **Export pipeline** — Codex wrote the initial weasyprint PDF converter and ebooklib EPUB exporter, then GPT-5.6 optimized the page layouts and styling for proper print formatting.

The combination of Codex's rapid code generation and GPT-5.6's reasoning capabilities meant the entire project went from concept to a working deployed product in a single weekend.

---

## 📋 Submission Checklist

- ✅ Public GitHub repo (All Rights Reserved — replaces MIT for hackathon protection)
- ✅ Proof of Alibaba Cloud deployment (see `docs/alibaba-proof.md`)
- ✅ Architecture diagram (see `docs/architecture.md`)
- ✅ Track identification: Codex Build Week
- ✅ All API calls use Qwen Cloud exclusively
- ✅ Working CLI and web UI

---

## 📄 License

**All Rights Reserved.** This project is submitted for the OpenAI Build Week
2026 Codex Hackathon for judging purposes only. Except as granted to hackathon
organizers and judges for evaluation, no part of this repository may be
reproduced, distributed, or transmitted without prior written permission.

See [LICENSE](./LICENSE) for full terms. The repository will be taken private
after the hackathon winner announcement.

# Imaginate ✦

> **One prompt → complete illustrated storybook with narration, multi-format exports**

[![Track](https://img.shields.io/badge/Track-AI%20Showrunner-c47a1a)]()
[![Qwen Cloud](https://img.shields.io/badge/Powered%20by-Qwen%20Cloud-2563eb)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()

---

## 🏆 Global AI Hackathon Series with Qwen Cloud

**Track:** AI Showrunner (Primary) + Autopilot Agent (Secondary)
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
- Qwen Cloud API key ([sign up](https://www.qwencloud.com) — $40 free credits)

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

## 📋 Submission Checklist

- ✅ Public GitHub repo with MIT license
- ✅ Proof of Alibaba Cloud deployment (see `docs/alibaba-proof.md`)
- ✅ Architecture diagram (see `docs/architecture.md`)
- ✅ Track identification: AI Showrunner
- ✅ All API calls use Qwen Cloud exclusively
- ✅ Working CLI and web UI

---

## 📄 License

MIT

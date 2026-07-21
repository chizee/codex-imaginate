# Imaginate — AI Deployment Agent Guide

Give this file to your AI coding agent (Claude Code, Cursor, etc.) to deploy Imaginate on Alibaba Cloud ECS.

## Mission

Deploy the Imaginate AI storybook generator to production on a fresh Alibaba Cloud ECS instance (Ubuntu 22.04). Repo: `https://github.com/chizee/imaginate-ai`.

## Step 1: SSH In

The user provides SSH access. Connect:
```
ssh -i <key.pem> root@<server-ip>
```

## Step 2: Clone & Run Setup

```bash
cd /root
git clone https://github.com/chizee/imaginate-ai.git
cd imaginate-ai
bash alibaba_deploy/setup-server.sh
```

This installs: Python 3.12, nginx, ffmpeg, certbot, creates a systemd service, and configures the nginx reverse proxy.

## Step 3: Set API Key

Edit `/etc/systemd/system/imaginate.service` and replace `CHANGE_ME` with the actual API key:
```
Environment="DASHSCOPE_API_KEY=sk-ws-H.XIDLXE.Dklu..."
```

Then:
```bash
sudo systemctl daemon-reload && sudo systemctl restart imaginate
```

## Step 4: SSL

```bash
sudo certbot --nginx -d imaginate.ai -d www.imaginate.ai
```

## Step 5: Verify

```bash
curl https://imaginate.ai/api/health
# Expected: {"status":"ok","version":"1.0.0"}
```

## Key Files

| File | Purpose |
|------|---------|
| `web_ui/backend/main.py` | FastAPI server |
| `web_ui/frontend/landing.html` | Landing page |
| `web_ui/frontend/index.html` | Dashboard (story generator) |
| `alibaba_deploy/setup-server.sh` | One-click server setup |
| `alibaba_deploy/Dockerfile` | Docker image |

## Important

- Rate limiting: 3 pipeline reqs / 5 min per IP
- Beta mode: free during beta, subscription coming later
- Qwen API key must be set in the systemd service file
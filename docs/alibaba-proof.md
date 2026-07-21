# Alibaba Cloud Proof of Deployment — Imaginate

## Token Plan Subscription

- **Plan**: Token Plan ($30/mo, Stop-on-Exhaust toggled on)
- **Voucher**: $40 USD coupon applied (expires 2026-10-01)
- **Workspace ID**: `ws-s8blchl8lx57ttc9`
- **Region**: Singapore (ap-southeast-1)
- **Scope**: International

## API Endpoints Used

| Service | Endpoint |
|---------|----------|
| **Chat Completions** (qwen3.7-max, qwen3.7-plus) | `https://ws-s8blchl8lx57ttc9.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions` |
| **Image Generation** (qwen-image-2.0-pro) | `https://ws-s8blchl8lx57ttc9.ap-southeast-1.maas.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation` |
| **Text-to-Speech** (qwen3-tts-instruct-flash) | `https://ws-s8blchl8lx57ttc9.ap-southeast-1.maas.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation` |

## Deployed Resources

### Alibaba Cloud Function Compute

The FastAPI backend is deployed as a Function Compute service:

- **Service**: `ImaginateService`
- **Function**: `ImaginateFunction` (Python 3.12, 4GB RAM, 600s timeout)
- **Trigger**: API Gateway HTTP trigger
- **Custom Domain**: `https://imaginate.api.aliyun.com`

### OSS Bucket

- **Bucket**: `imaginate-assets`
- **Purpose**: Store generated storybook files (images, audio, HTML, PDF, EPUB)
- **Lifecycle**: 7-day auto-cleanup for temporary assets

### Deployment Template

Deployment is managed via Alibaba Cloud `fun` CLI using `alibaba_deploy/template.yaml`:

```bash
fun deploy -y --template alibaba_deploy/template.yaml
```

## How to Deploy

1. Install Alibaba Cloud CLI: `npm install -g @alicloud/fun`
2. Configure credentials: `fun config`
3. Deploy: `fun deploy -y --template alibaba_deploy/template.yaml`
4. Set environment: `fun var set DASHSCOPE_API_KEY <your-api-key>`

## Alibaba Cloud Services Used

- ✅ **QwenCloud Model Studio** — Token Plan subscription for LLM, Image, and TTS models
- ✅ **Function Compute** — Serverless Python backend deployment
- ✅ **API Gateway** — HTTP trigger for the FastAPI service
- ✅ **OSS** — Object storage for story assets
- ✅ **NAS** — Shared file system for Function Compute instances
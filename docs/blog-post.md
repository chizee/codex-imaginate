# Building Imaginate: One Prompt to an Illustrated Storybook with Qwen Cloud

*How I built a full AI storybook generator for the Global AI Hackathon Series using Qwen3.7-max, Qwen Image 2.0 Pro, and Qwen3-tts-instruct-flash — all on Alibaba Cloud.*

---

## The Idea

What if a parent could type "a brave little fox discovers a magical garden" and get a complete, illustrated, narrated storybook in minutes? No design skills, no writing, no recording.

That is Imaginate.

## The Stack

Built entirely on **Qwen Cloud via Alibaba Cloud Token Plan**:
- **Qwen3.7-max** for script generation (structured JSON output)
- **Qwen Image 2.0 Pro** for character-consistent scene illustrations
- **Qwen3-tts-instruct-flash** for natural English narration (Ethan voice)

## The Challenge

The workspace endpoint rejected reference images alongside text. The fix: embed character descriptions from the bible directly into scene prompts. Rate limiting at ~4 images/min required 15-second delays with aggressive 429 backoff.

## The Result

One prompt produces: story script, character references, scene illustrations, narration MP3s, and a self-contained 20MB+ HTML storybook with swipe navigation and audio. Plus PDF and EPUB exports.

**Total cost per story:** ~$0.62.

Try it: [github.com/chizee/imaginate-ai](https://github.com/chizee/imaginate-ai)

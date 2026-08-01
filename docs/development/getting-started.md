# Development Setup

## Current Upstream Stack

- Python 3.12 managed by `uv`.
- Node.js 20+ for the Electron/React desktop app.
- FastAPI and SQLite in the local service.
- Optional FFmpeg and CUDA depending on the selected media and model adapters.

## Clone

```bash
git clone https://github.com/aaronfang/BiliSum-Research.git
cd BiliSum-Research
git remote add upstream https://github.com/lycohana/BiliSum.git
```

The GitHub fork may already configure `upstream` when cloned through GitHub CLI. Confirm with `git remote -v` before adding it.

## Install

```bash
uv sync --python 3.12 --all-packages
npm install --prefix apps/desktop
```

Copy `.env.example` to `.env` and keep credentials out of version control.

## Run

```bash
npm run dev
```

To run only the backend:

```bash
uv run --package video-sum-service python -m video_sum_service
```

## Test

```bash
uv run pytest
npm test --prefix apps/desktop
npm run typecheck --prefix apps/desktop
```

The MVP must have an offline test profile. Unit and integration tests should inject in-memory or fixture adapters for platform subtitles, ASR, OCR, visual inference, search, HTTP verification, and Obsidian writes.

## First Framework Slice

Do not scaffold every proposed package at once. Start with Milestone 0 and 1:

1. Add characterization tests for the current local media pipeline.
2. Introduce Transcript and Transcript Source models.
3. Implement a sidecar subtitle adapter.
4. Put current Bilibili subtitle and ASR paths behind TranscriptResolver.
5. Persist provenance without changing existing UI output.

This creates the first real seam and keeps the interface as the test surface.

## Local Model Development

Keep model processes outside the FastAPI process. The application should call injected adapters so tests do not load weights.

Recommended target adapters:

- Qwen3-ASR 1.7B and 0.6B, plus Qwen3 ForcedAligner.
- Existing FunASR and Whisper adapters as fallbacks.
- Qwen3-VL 4B or 8B through an OpenAI-compatible local endpoint.
- RapidOCR for the first OCR implementation.
- SearXNG as a separate container when link discovery is enabled.

Hardware profiles and defaults must be benchmarked on target machines before being documented as supported.

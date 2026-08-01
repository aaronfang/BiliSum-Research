# Proposed Configuration

These names establish configuration ownership; implementation may refine exact serialization while preserving the concepts.

```env
# Privacy and network
VIDEO_RESEARCH_MODE=local-first
VIDEO_RESEARCH_ALLOW_CLOUD_MODELS=false
VIDEO_RESEARCH_ALLOW_DISCOVERY_NETWORK=true

# Transcript resolution
VIDEO_RESEARCH_TRANSCRIPT_ORDER=sidecar,platform_manual,platform_auto,local_asr
VIDEO_RESEARCH_SIDECAR_LANGUAGES=zh-CN,zh,en
VIDEO_RESEARCH_LOCAL_ASR_PROVIDER=qwen3-asr
VIDEO_RESEARCH_LOCAL_ASR_MODEL=Qwen/Qwen3-ASR-1.7B

# Evidence
VIDEO_RESEARCH_VISUAL_PROVIDER=openai-compatible
VIDEO_RESEARCH_VISUAL_MODEL=Qwen3-VL-8B-Instruct
VIDEO_RESEARCH_VISUAL_BASE_URL=http://127.0.0.1:8001/v1
VIDEO_RESEARCH_FRAMES_PER_HOUR=120
VIDEO_RESEARCH_CLIP_MAX_SECONDS=15

# Resource pools
VIDEO_RESEARCH_DOWNLOAD_CONCURRENCY=2
VIDEO_RESEARCH_ASR_CONCURRENCY=1
VIDEO_RESEARCH_VISUAL_CONCURRENCY=1
VIDEO_RESEARCH_LINK_CONCURRENCY=4

# Link verification
VIDEO_RESEARCH_SEARXNG_URL=http://127.0.0.1:8080
VIDEO_RESEARCH_VERIFY_LINKS=true

# Obsidian
VIDEO_RESEARCH_OBSIDIAN_VAULT=
VIDEO_RESEARCH_OBSIDIAN_MODE=dry-run
VIDEO_RESEARCH_OBSIDIAN_ATTACHMENTS=Attachments/BiliSumResearch
```

## Rules

- `offline` mode overrides every network-enabled option to false.
- Cloud configuration is invalid unless `ALLOW_CLOUD_MODELS=true`.
- Secrets are never stored in notes, task artifacts, logs, or research reports.
- A task snapshot records effective non-secret configuration and model identifiers.
- Obsidian sync refuses a missing or ambiguous vault path; it never guesses a home directory.

# Foundation Analysis

## Decision Summary

No mature open-source project inspected provides the complete workflow of accurate transcription, frame-assisted correction, verified tool links, batch processing, Obsidian-native publishing, and bounded topic research.

BiliSum is the closest product foundation because it already supplies local and remote video ingestion, several ASR paths, visual notes, a desktop app, SQLite task history, a knowledge base, and Markdown/Obsidian export under the MIT license.

## Important Source-Level Gap

In BiliSum v1.19.2, the local media pipeline calls transcription and summarization before visual-note generation. Visual observations can enrich a final note but do not reconcile the Transcript. The visual prompt selects a small set of illustrations based on the already-generated text; it is not an evidence-verification loop.

- [Local media pipeline](https://github.com/lycohana/BiliSum/blob/73eebcb6f26efe434c83c4c9dfa1bb175b791c7f/packages/core/src/video_sum_core/pipeline/real.py#L564-L603)
- [Visual prompts](https://github.com/lycohana/BiliSum/blob/73eebcb6f26efe434c83c4c9dfa1bb175b791c7f/packages/infra/src/video_sum_infra/config.py#L231-L341)

BiliSum currently prefers Bilibili subtitles and falls back to ASR, but that logic is platform-specific. `TaskOptions.prefer_subtitles` does not yet provide a cross-source TranscriptResolver.

- [Task models](https://github.com/lycohana/BiliSum/blob/master/packages/core/src/video_sum_core/models/tasks.py)
- [Pipeline subtitle branch](https://github.com/lycohana/BiliSum/blob/master/packages/core/src/video_sum_core/pipeline/real.py)

## Candidate Comparison

| Project | Useful capability | Why it is not the base |
|---|---|---|
| [Watch Skill](https://github.com/oxbshw/watch-skill) | Scene-aware frames, OCR, local transcription, evidence retrieval, batch library | Agent-oriented evidence layer, not a complete note/research desktop product |
| [tldw_server](https://github.com/rmusser01/tldw_server) | Media RAG, web research, outputs | Video ingestion is audio-only by default; broader and GPL-3.0 |
| [VideoLingo](https://github.com/Huanshere/VideoLingo) | WhisperX and strong subtitle workflow | Focuses on subtitles, translation, and dubbing |
| [VideoRAG](https://github.com/HKUDS/VideoRAG) | Long-video multimodal retrieval | Heavy deployment, question-answering shape, and a non-commercial dependency in the complete implementation |

Watch Skill remains a useful design reference for scene budgets, perceptual frame deduplication, OCR retries, timestamped evidence, and cross-video search.

## Open-Source Building Blocks

- [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR): local multilingual ASR and forced alignment.
- [Qwen3-VL](https://github.com/QwenLM/Qwen3-VL): local visual and video understanding with OCR.
- [PySceneDetect](https://github.com/Breakthrough/PySceneDetect): content-aware scene detection.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp): downloads, playlists, searches, subtitles, URL batches, and download archives.
- [SearXNG](https://github.com/searxng/searxng): self-hosted metasearch for candidate discovery.

## Fork Rationale

The planned product reuses more of BiliSum than it replaces. A GitHub fork preserves attribution and upstream comparison, while focused module interfaces limit merge conflicts. See [ADR 0001](../adr/0001-maintain-a-named-github-fork.md).

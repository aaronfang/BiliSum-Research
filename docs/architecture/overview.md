# Architecture Overview

## Architectural Direction

Keep BiliSum’s existing Electron UI, FastAPI application, SQLite repository, task worker, media ingestion, knowledge base, and exporters. Add focused modules behind small interfaces so upstream changes remain mergeable and local model or platform choices remain adapters.

```text
Inputs
  -> TranscriptResolver
  -> TextAnalyzer
  -> EvidenceEngine
  -> FusionEngine
  -> LinkResolver
  -> NotePublisher

BatchRunner coordinates Analysis Jobs.
ResearchCampaignEngine discovers and selects inputs, then delegates to BatchRunner.
```

## Existing Code Reused

| Capability | Existing location |
|---|---|
| Task models and options | `packages/core/src/video_sum_core/models/tasks.py` |
| Main processing pipeline | `packages/core/src/video_sum_core/pipeline/real.py` |
| Background queues | `apps/service/src/video_sum_service/worker.py` |
| SQLite persistence | `apps/service/src/video_sum_service/repository.py` |
| Task HTTP routes | `apps/service/src/video_sum_service/routers/tasks.py` |
| Knowledge index and RAG | `apps/service/src/video_sum_service/knowledge/` |
| Markdown and Obsidian export | `packages/core/src/video_sum_core/markdown_exports.py` and task export modules |

The first refactor should extract orchestration from `RealPipelineRunner` without changing its external behavior. New modules should not reach into Electron or FastAPI concerns.

## Deep Modules

### TranscriptResolver

Interface:

```python
resolve(source: MediaSource, policy: TranscriptPolicy) -> Transcript
```

It hides sidecar discovery, platform subtitles, language selection, subtitle normalization, ASR fallback, forced alignment, and provenance. Adapters exist for local sidecars, Bilibili, yt-dlp subtitles, Qwen3-ASR, FunASR, and Whisper.

Invariant: returned timed text always identifies its Transcript Source. A subtitle failure may fall back; it must not silently change provenance.

### TextAnalyzer

Interface:

```python
analyze(transcript: Transcript, brief: AnalysisBrief) -> TextAnalysis
```

It hides chaptering, entity extraction, Claim extraction, uncertainty detection, and Text Anchor planning. It does not read video frames.

### EvidenceEngine

Interface:

```python
collect(media: MediaSource, anchors: list[TextAnchor], budget: EvidenceBudget) -> EvidenceSet
```

It hides scene detection, interval selection, frame-quality ranking, perceptual deduplication, OCR, clip extraction, zoom/retry behavior, and visual-model calls.

Invariant: every Evidence item has source media, timestamp or interval, derivation method, and confidence.

### FusionEngine

Interface:

```python
reconcile(transcript: Transcript, evidence: EvidenceSet) -> CorrectedTranscript
```

It hides candidate generation, character-level checks for commands and URLs, conflict handling, thresholds, and audit creation.

Invariant: raw Transcript content remains immutable. Unsupported edits are alternatives, not automatic Corrections.

### LinkResolver

Interface:

```python
resolve(references: list[ToolReference], policy: LinkPolicy) -> list[ResolvedTool]
```

It hides registry lookup, GitHub identity checks, SearXNG search, redirect handling, official-domain ranking, and unresolved fallback. Network, GitHub, package-registry, and in-memory adapters sit at internal seams.

Invariant: only deterministic checks can produce `verified`; an LLM score alone cannot.

### NotePublisher

Interface:

```python
publish(bundle: KnowledgeBundle, target: PublishTarget) -> PublicationResult
```

It hides Markdown rendering, YAML properties, wikilinks, attachment placement, managed blocks, collision handling, dry-run previews, and index updates. Initial adapters are export-directory and Obsidian-vault.

Invariant: synchronization does not overwrite user-authored content outside managed regions.

### BatchRunner

Interface:

```python
submit(plan: BatchPlan) -> BatchRunId
status(batch_id: BatchRunId) -> BatchStatus
cancel(batch_id: BatchRunId) -> BatchStatus
```

It hides input expansion, content-hash deduplication, resource-specific scheduling, retry policy, checkpoints, and aggregate progress.

### ResearchCampaignEngine

Interface:

```python
start(brief: ResearchBrief) -> ResearchCampaignId
status(campaign_id: ResearchCampaignId) -> CampaignStatus
```

It hides query planning, discovery, cheap screening, selection, budget accounting, incremental searches, cross-source synthesis, and stop conditions. It delegates selected media to BatchRunner instead of duplicating video processing.

## Pipeline State

```text
discovered -> transcript_resolved -> text_analyzed -> evidence_collected
  -> transcript_reconciled -> links_resolved -> note_published
```

Each transition records input hashes, configuration version, model identifiers, start/end timestamps, output artifact references, and error state. A stage is reusable only when all cache keys match.

## Persistence

Extend SQLite with additive migrations. Keep large binary artifacts on disk and store references plus hashes in SQLite.

Proposed records:

- `analysis_jobs`, `analysis_stages`
- `transcripts`, `transcript_segments`, `corrections`
- `text_anchors`, `evidence_items`
- `tool_references`, `resolved_tools`
- `batch_runs`, `batch_members`
- `research_campaigns`, `campaign_sources`, `campaign_claims`
- `publications`

Use stable IDs derived from source identity and content hashes where possible. Never use display titles as identity.

## Resource Scheduling

Use separate concurrency pools for download, ASR, VLM, embedding, LLM, and link verification. The visual pool defaults to one worker. A Batch Run carries explicit limits for total media duration, disk usage, retries, frames per hour, and optional network requests.

## Local And Network Modes

| Mode | Media/derived data | Network use |
|---|---|---|
| Offline | Local only | Denied; links remain observed or unresolved |
| Local-first | Local models | Discovery, download, and deterministic link verification only |
| Hybrid | Local by default | Explicitly selected cloud adapters receive disclosed payloads |

All external adapters receive an egress policy. No module creates a cloud client internally.

## Proposed Package Shape

```text
packages/core/src/video_sum_core/
  transcript/
  analysis/
  evidence/
  fusion/
  links/
  publishing/
  batch/
  research/

apps/service/src/video_sum_service/
  routers/batches.py
  routers/evidence.py
  routers/research.py
  migrations/
```

Do not create all packages up front. Add each package with its first end-to-end behavior slice.

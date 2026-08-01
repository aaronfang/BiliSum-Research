# MVP Specification

## Objective

Deliver one reliable local workflow:

> Given a directory of technical videos and optional sidecar subtitles, produce Obsidian-ready Source Notes with accurate timed text, evidence-backed corrections for high-value technical tokens, selected frames, and resumable batch status.

This MVP deliberately excludes automatic topic discovery. Research Campaigns build on the same completed Analysis Job and Batch Run interfaces in a later milestone.

## Supported Inputs

- A local video file.
- A local directory scanned non-recursively in the first slice.
- Sidecar `.srt` and `.vtt` files with the same stem as the media file.
- Existing BiliSum single URL behavior must continue to work.

## Required Behavior

### Transcript Resolution

- Prefer an accepted sidecar subtitle over ASR.
- Normalize subtitle segments into a common timed structure.
- Fall back to the configured local ASR adapter when no usable subtitle exists.
- Persist Transcript Source, language, model, and fallback reason.
- Keep the original Transcript immutable.

### Text Analysis

- Extract candidate tool names, commands, URLs, versions, and numeric claims.
- Mark uncertain or conflicting phrases.
- Create time-bound Text Anchors only for high-value candidates.

### Visual Evidence

- Select frames inside Text Anchor intervals using scene/OCR change and image-quality signals.
- Enforce a configurable frame budget.
- Store selected frame, timestamp, OCR, derivation method, and confidence.
- Support a query that returns frames for a text phrase or Tool Reference.

### Correction

- Automatically correct only technical tokens supported by audio/text and visual Evidence.
- Store from/to values, Evidence IDs, confidence, rule/model version, and decision.
- Keep uncertain alternatives without changing the Transcript.

### Batch Processing

- Expand a directory into one Analysis Job per supported media file.
- Deduplicate by content hash.
- Continue after an individual failure.
- Expose queued/running/completed/failed/cancelled counts.
- Resume incomplete jobs after service restart without repeating completed stages.

### Obsidian Publication

- Provide export, dry-run, and sync modes.
- Create a Source Note with YAML properties, corrected transcript, corrections, and frame links.
- Create or update a Topic Index for the batch.
- Use stable relative attachment paths.
- Preserve user text outside managed generated regions.

## Proposed HTTP Surface

```text
POST /api/v1/batches
GET  /api/v1/batches/{batch_id}
POST /api/v1/batches/{batch_id}/cancel

POST /api/v1/tasks/{task_id}/evidence/search
POST /api/v1/tasks/{task_id}/evidence/verify

POST /api/v1/batches/{batch_id}/publish
POST /api/v1/batches/{batch_id}/publish/dry-run
```

The request and response schemas are defined when implementing each vertical slice; these paths establish ownership, not final wire details.

## Acceptance Criteria

1. A fixture directory containing three videos, two sidecar subtitles, and one duplicate creates three unique Analysis Jobs and uses ASR only once.
2. Restarting the service after transcript resolution resumes at text analysis.
3. A deliberately misrecognized tool name is corrected only when a matching frame/OCR Evidence item exists.
4. A conflicting or blurry frame produces an uncertain alternative, not an automatic Correction.
5. Text search for a tool returns the matching frame and transcript interval.
6. Obsidian dry-run lists all planned writes without modifying the vault.
7. Sync creates valid wikilinks and attachments, then a second sync is idempotent.
8. User text added outside generated regions survives republishing.
9. All tests run without network access or cloud credentials.

## Quality Gates

- Technical entity, command, and URL exact-match F1: at least 95% on the evaluation set.
- Automatic correction precision: at least 98%.
- Fabricated verified URLs: zero.
- Generated wikilink and attachment integrity: 100%.
- Completed-stage reuse after restart: 100% for test fixtures.

## Deferred

- Recursive directories and file watching.
- YouTube and Bilibili playlists as Batch Run inputs.
- Automatic tool-link discovery and verification.
- Cross-video Claim synthesis.
- Research Campaigns and automatic video discovery.
- Cloud model adapters in the primary acceptance path.

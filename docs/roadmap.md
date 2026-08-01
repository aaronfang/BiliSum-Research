# Implementation Roadmap

Each milestone delivers an end-to-end behavior slice. Later milestones depend on the interfaces and persisted artifacts of earlier ones.

## Milestone 0: Preserve Upstream Behavior

- Add architecture characterization tests around local media, Bilibili subtitle fallback, task persistence, and Markdown export.
- Extract no modules until a characterization test protects the behavior being moved.
- Add additive migration infrastructure and schema-version reporting.

Exit: the fork can sync upstream and prove no baseline regression.

## Milestone 1: Transcript Resolver

- Introduce Transcript and Transcript Source domain models.
- Support local `.srt` and `.vtt` sidecars.
- Move current Bilibili subtitle and ASR fallback behind TranscriptResolver.
- Persist provenance and stage checkpoints.

Exit: single local media analysis uses sidecar-first resolution and resumes after restart.

## Milestone 2: Resumable Batch Run

- Directory expansion and content-hash deduplication.
- Batch records, member status, cancellation, retries, and aggregate progress.
- Separate resource pools beginning with CPU/ASR and visual work.

Exit: the MVP fixture batch passes restart, duplicate, and partial-failure tests.

## Milestone 3: Text Anchors And Evidence

- Extract high-value technical candidates.
- Select frames around timed anchors.
- Add OCR, frame-quality scoring, perceptual deduplication, and evidence persistence.
- Implement text-to-frame search and Claim verification endpoints.

Exit: a tool mention can retrieve a relevant frame without analyzing the full video visually.

## Milestone 4: Evidence-Backed Correction

- Introduce Correction and Corrected Transcript.
- Add deterministic checks for commands, URLs, versions, and identifiers.
- Add model-assisted proposals behind conservative thresholds.
- Surface audit records and uncertain alternatives in the UI.

Exit: correction precision meets the MVP gate on a labeled corpus.

## Milestone 5: Obsidian Publisher

- Implement export, dry-run, and sync adapters.
- Generate Source Notes, Entity Notes, and Topic Indexes with stable IDs and attachments.
- Protect user-authored content with managed regions and conflict reporting.

Exit: repeated publishing is idempotent and link-integrity tests pass.

## Milestone 6: Verified Tool Links

- Add package-registry, GitHub, direct-URL, and SearXNG adapters.
- Add deterministic identity checks and verified/probable/unresolved states.
- Create Entity Notes and connect them to Source Notes.

Exit: verified URL precision meets the quality gate and fabricated URLs remain zero.

## Milestone 7: Remote Batch Sources

- Add URL files, playlists, and platform subtitles.
- Use yt-dlp download archives and staged downloads.
- Download metadata/subtitles first; download media only for selected sources or visual Evidence.

Exit: a playlist Batch Run respects budgets, deduplicates, and resumes.

## Milestone 8: Research Campaign

- Introduce Research Brief, query planning, source screening, and budgets.
- Reuse BatchRunner for selected media.
- Add cross-video entity merging, Claim comparison, source typing, and stop conditions.
- Publish Topic Reports and Topic Indexes.

Exit: the “open-source virtual-human projects” acceptance campaign produces a traceable Obsidian research set.

## Milestone 9: Product Hardening

- Evaluation dashboard, resource estimates, and data-egress preview.
- Migration, backup, recovery, and upstream-sync exercises.
- Packaging for supported macOS/Windows profiles and documented Linux/Docker behavior.

# Repository Guide

This fork extends BiliSum into a local-first, evidence-driven video research system.

## Read First

Before changing behavior, read:

1. `CONTEXT.md` for canonical domain language.
2. `docs/product/vision.md` for scope and non-goals.
3. `docs/architecture/overview.md` for module interfaces and seams.
4. `docs/specs/mvp.md` for the current delivery target.
5. Relevant ADRs under `docs/adr/`.

## Engineering Rules

- Preserve the upstream BiliSum workflow unless a requirement explicitly replaces it.
- Keep media, transcripts, frames, embeddings, and notes local by default.
- Cloud providers are opt-in adapters. Tests must not require network access.
- Prefer subtitles before ASR. Use visual models only for selected text anchors or explicit user requests.
- Keep raw transcripts immutable. Corrections require evidence and an audit record.
- Never mark a URL as verified without deterministic validation.
- Write behavior tests through module interfaces; avoid tests coupled to implementation details.
- Add migrations for persisted schema changes. Batch jobs must resume after process restart.
- Generated Obsidian content must not overwrite user-authored content outside managed blocks.

## Upstream Discipline

- `origin` is this fork; `upstream` is `lycohana/BiliSum`.
- Keep research features in focused modules and adapters to reduce upstream merge conflicts.
- Do not reformat or rename unrelated upstream files.
- Record hard-to-reverse deviations from upstream in `docs/adr/`.

## Verification

Run the narrowest relevant checks first, then the full suites before merging:

```bash
uv run pytest
npm test --prefix apps/desktop
npm run typecheck --prefix apps/desktop
```

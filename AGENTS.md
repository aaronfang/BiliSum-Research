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

## Delivery And Release Rules

- Treat `master` as protected. Never commit or push directly to local or remote `master`.
- Every repository change starts from a GitHub Issue, including fixes, features, refactors,
  documentation, dependency updates, release preparation, and upstream synchronization.
- Create a focused branch from the latest `origin/master`. Include the Issue number in the
  branch name, for example `fix/issue-123-subtitle-error` or
  `chore/issue-123-upstream-sync`.
- Use Conventional Commits. Each PR must contain a closing reference such as `Closes #123`.
- Push only the topic branch. Deliver changes through a PR to `master`; never bypass required
  checks, unresolved review conversations, or the repository's branch protection.
- Do not merge a PR, create a tag, publish a GitHub Release, or push release artifacts unless
  the user explicitly asks for that delivery step after the PR is approved and green.
- After a PR is merged and `master` is confirmed healthy, delete its remote and local topic
  branches. Never delete an unmerged branch, the current branch, a branch with unique commits,
  or any branch/worktree containing uncommitted changes. Keep release or long-lived maintenance
  branches only when the repository explicitly requires them.
- Releases contain only changes already merged to `master`. The repository-owned release
  workflow may create its generated version commit and tag after a merge; this is the sole
  direct-mutation exception and is not permission for hand-authored changes.
- Follow `docs/development/delivery-workflow.md` for the complete workflow and emergency policy.

## Verification

Run the narrowest relevant checks first, then the full suites before merging:

```bash
uv run pytest
npm test --prefix apps/desktop
npm run typecheck --prefix apps/desktop
```

# Upstream Synchronization

This repository remains a GitHub fork of `lycohana/BiliSum` so upstream fixes and product improvements can be reviewed and merged.

## Remotes

```text
origin    https://github.com/aaronfang/BiliSum-Research.git
upstream  https://github.com/lycohana/BiliSum.git
```

## Sync Procedure

Perform synchronization on a clean working tree:

```bash
git fetch upstream
git switch master
git merge --ff-only upstream/master
git push origin master
```

If the fork has diverged, create a dedicated sync branch and merge normally after tests. Do not force-push `master` to hide divergence.

## Conflict Reduction

- Keep new domain logic in the proposed `packages/core/src/video_sum_core/` modules.
- Add service routers instead of expanding the existing task router indefinitely.
- Change `RealPipelineRunner` through narrow delegation commits protected by characterization tests.
- Avoid reformatting upstream files.
- Keep fork-specific documentation and ADRs additive.

## Sync Verification

After merging upstream:

```bash
uv run pytest
npm test --prefix apps/desktop
npm run typecheck --prefix apps/desktop
```

Also rerun the local batch smoke fixture once it exists. Upstream sync is incomplete until migrations and resume behavior are verified.

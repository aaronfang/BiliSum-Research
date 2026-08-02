# Upstream Synchronization

This repository remains a GitHub fork of `lycohana/BiliSum` so upstream fixes and product improvements can be reviewed and merged.

## Remotes

```text
origin    https://github.com/aaronfang/BiliSum-Research.git
upstream  https://github.com/lycohana/BiliSum.git
```

## Sync Procedure

Perform synchronization on a clean working tree through an Issue-scoped branch and PR:

```bash
git fetch upstream
git switch master
git pull --ff-only origin master
git switch -c chore/issue-<number>-upstream-sync
git merge upstream/master
git push -u origin chore/issue-<number>-upstream-sync
gh pr create --base master --head chore/issue-<number>-upstream-sync \
  --title "chore(upstream): sync upstream master" \
  --body "Closes #<number>"
```

Do not push, force-push, or merge upstream directly into remote `master`. Resolve divergence on
the sync branch, run the required checks, and merge only after the PR is green and approved. See
`docs/development/delivery-workflow.md` for the repository-wide policy.

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

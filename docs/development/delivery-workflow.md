# Delivery Workflow

This document is the canonical submission, push, merge, and release policy for
`aaronfang/BiliSum-Research`.

## Protected Branch

`master` is the remote trunk and is protected.

- Do not develop on, commit to, or push directly to `master`.
- Do not force-push or delete `master`.
- Do not use administrator bypass to avoid the normal delivery flow.
- Pushes are limited to topic branches associated with an Issue.

The only direct mutation allowed on `master` is a version commit and tag produced by the
repository-owned release workflow after an approved PR has merged. Human-authored and
agent-authored changes never use this exception.

## Required Flow

Every change, including documentation, dependency maintenance, release preparation, and
upstream synchronization, uses this sequence:

1. Search existing Issues, then create or select one that defines the need and acceptance
   criteria.
2. Update local `master` from `origin/master` without adding local commits.
3. Create a focused topic branch whose name includes the Issue number.
4. Make narrow commits using Conventional Commits and run the relevant checks.
5. Push the topic branch only.
6. Open a PR to `master` containing `Closes #<issue-number>` or an equivalent closing keyword.
7. Resolve review conversations and wait for every required check to pass.
8. Merge through GitHub. After the merge and post-merge checks are healthy, safely delete the
   remote and local topic branch.
9. Publish a release only from the resulting `master` state.

Example:

```bash
git switch master
git pull --ff-only origin master
git switch -c fix/issue-123-subtitle-error

# edit and verify
git commit -m "fix(subtitle): handle missing subtitle URL"
git push -u origin fix/issue-123-subtitle-error
gh pr create --base master --head fix/issue-123-subtitle-error \
  --title "fix(subtitle): handle missing subtitle URL" \
  --body "Closes #123"
```

## Pull Request Gate

A PR is mergeable only when:

- it closes at least one repository Issue;
- its scope and behavior match the Issue;
- required CI and PR-policy checks pass;
- relevant tests and documentation are included;
- all review conversations are resolved;
- a maintainer has accepted the result.

Branch protection is the enforcement layer. `AGENTS.md` is the persistent instruction layer for
automation and future conversations.

## Branch Cleanup

Topic branches are temporary. Delete them after their PR is merged and the resulting `master`
commit is confirmed healthy; the merged PR and Git history retain the review and commits.

Before deleting a branch, confirm all of the following:

- the PR is merged rather than merely closed;
- the merge commit is present on `origin/master`;
- required post-merge checks are not failing;
- the branch has no unique work that was excluded from the merge;
- no worktree using the branch contains uncommitted changes.

Then clean up from a safe branch or worktree:

```bash
git switch master
git pull --ff-only origin master
git push origin --delete <topic-branch>
git branch -d <topic-branch>
git fetch --prune
```

Never force-delete an unmerged branch to make cleanup succeed. Do not switch branches or remove
a worktree when that could carry, overwrite, or discard uncommitted changes. Release branches and
long-lived maintenance branches are retained only when their lifecycle is explicitly documented.

## Release Gate

A release is a separate delivery step after merge, not a side effect agents may initiate on
their own.

- Never release from an unmerged PR branch or a dirty working tree.
- Never tag a commit that is not reachable from `origin/master`.
- Version selection follows the repository's existing Conventional Commit detection:
  `feat*:` or `feat(scope)*:` requests a minor release;
  `fix*:`, `perf*:`, `refactor*:` and their scoped forms request a patch release;
  `!` or a `BREAKING CHANGE` footer requests a major release. A commit without `*`, `!`, or
  `BREAKING CHANGE` does not request a release.
- The release workflow owns generated version commits, tags, GitHub Releases, and artifacts.
- An agent waits for explicit user authorization before manually dispatching, retrying, or
  repairing a release.

## Upstream Synchronization

Upstream synchronization follows the same Issue and PR path. Fetch `upstream/master`, create an
Issue-scoped sync branch from `origin/master`, merge upstream into that branch, verify, push the
branch, and open a PR. Never push a fetched or merged upstream commit directly to `master`.

## Emergency Changes

Urgency does not authorize a direct push. Open an emergency Issue and PR, keep the diff minimal,
run the required checks, and merge through the protected branch. If GitHub itself prevents that
flow, record the incident and recovery plan before a repository administrator changes protection;
restore protection immediately afterward.

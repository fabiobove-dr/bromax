---
name: pr
description: Prepare, validate and squash-merge a Bromax pull request within the independent fork when authorized.
---

Root `AGENTS.md` defines the destination and branch/merge policy.

- Check `git remote -v`, worktree status and the issue's acceptance criteria.
  Use an isolated worktree if unrelated user changes would otherwise interfere.
- Summarize the final behavior and evidence using
  `.github/pull_request_template.md`; close only criteria actually fulfilled.
  Write multiline bodies to a temporary file and pass `--body-file`.
- Create with `gh pr create --repo fabiobove-dr/bromax --base main --head <branch>`.
  Inspect `gh pr checks <number> --repo fabiobove-dr/bromax` and review the final
  diff, including changes from conflict resolution. Diagnose failing or absent
  checks before deciding whether validation is adequate for the change.
- When merge is authorized and relevant gates pass, use
  `gh pr merge <number> --repo fabiobove-dr/bromax --squash --delete-branch
  --match-head-commit <validated-sha>`. Verify merged state and linked issue state.
  Do not bypass protection or rewrite published history to land a PR.

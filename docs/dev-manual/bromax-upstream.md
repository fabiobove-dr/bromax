# Upstream synchronization and patch provenance

Bromax develops independently in `fabiobove-dr/bromax`. Its source baseline is
upstream GROMACS `main` at
`3b6ed77e4e1839bdf80f39cd9e8d300576d1b41f` (2026-09-24,
“Enable leak checking for mdrun tests that no longer leak”), a 2027 development
tree. This is an upstream commit, not a released Bromax version or a statement
that all 2027 features are validated.

## Remote roles and cadence

`origin` is `git@github.com:fabiobove-dr/bromax.git` and the only push/PR
destination. An optional `upstream` remote reads
`https://github.com/gromacs/gromacs.git`; disable its push URL:

```sh
git remote add upstream https://github.com/gromacs/gromacs.git
git remote set-url --push upstream DISABLED
git fetch upstream main --tags
```

If that remote already exists, inspect its URLs before updating it. Never push
to upstream or open a Bromax PR there. The reporting workflow uses a direct
HTTPS fetch and a read-only token, so it does not depend on a local remote.

Review upstream divergence weekly and before a Bromax release. Prioritize
correctness, security and supported-platform fixes. The automated report only
lists commit/tag information; a contributor must assess relevance and validation.
No automation merges upstream changes or opens upstream PRs.

## Import strategy

For a localized fix, create a Bromax branch from updated `origin/main` and use
`git cherry-pick -x <upstream-sha>`. Keep the original commit reference in the
squashed commit/PR body, since squash merging otherwise loses its separate
commit identity. State whether the patch is unchanged or adapted and why.

For a coordinated upstream update, merge the selected upstream commit into a
Bromax feature branch, resolve conflicts there, validate it and open a PR to
Bromax `main`. The PR is squash-merged under the normal policy; preserve the
full upstream source SHA, previous baseline, merge base and import range in
its body and resulting squash message. Update this document's baseline in the
same PR. Never rebase or force-push published Bromax `main`. Rebase only an
unmerged feature branch when appropriate.

Squash importing a range does not retain upstream commits as ancestors. The
declared baseline and import references therefore remain authoritative for
provenance; a raw ahead/behind count is diagnostic, not proof a fix is missing.
For selectively imported patches, inspect their recorded source references
and patch content before proposing duplicates.

## Conflict-sensitive areas and validation

Treat these as elevated-review areas when Bromax diverges from upstream:

- `src/gromacs/ewald/`: PME, FFT planning and GPU kernels.
- `src/gromacs/nbnxm/`: nonbonded kernels, pair lists and reductions.
- `src/gromacs/mdlib/`, `mdrun/`, `modularsimulator/`, `gpu_utils/`, `domdec/`
  and `taskassignment/`: scheduling, dependencies, ownership and decomposition.
- Root and module `CMakeLists.txt`, `cmake/`, `.github/` and `admin/`:
  supported configurations, CI and scientific fixtures.

Resolve conflicts from the original behavioral invariants rather than choosing
one side wholesale. A sync PR records affected backends, precision and MPI
modes, normal Bromax CI results, and numerical/physical validation for changed
simulation behavior. Hot-path changes also need a reproducible performance
baseline. Required GPU evidence must be obtained on appropriate hardware;
unavailable evidence is an unmet merge gate.

## Reproducing the base and reviewing a patch

```sh
git fetch origin main
git fetch https://github.com/gromacs/gromacs.git main --no-tags
git show 3b6ed77e4e1839bdf80f39cd9e8d300576d1b41f
git merge-base origin/main FETCH_HEAD
git log --oneline origin/main..FETCH_HEAD
```

The initial inherited tree is exactly the baseline commit; Bromax PR #34 and
later PRs are fork changes above it. Check the PR history and preserved import
references to reconstruct subsequent updates. Every import PR must include:

```text
Upstream source: gromacs/gromacs@<full SHA> (and MR URL when available)
Previous baseline / import range:
Unchanged or adapted (reason and affected files):
Conflict-sensitive areas:
Bromax tests, scientific validation and performance evidence:
New baseline, if this is a coordinated sync:
```

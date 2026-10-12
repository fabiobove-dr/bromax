# Bromax development

## Repository and Git workflow

This repository is `fabiobove-dr/bromax`, an independently maintained GROMACS
fork. All pushes, issues and PRs for Bromax target this fork. Never push to or
open/target a PR against `gromacs/gromacs`. Upstream is read/fetch-only; imported
patches must retain their original commit/MR reference and explain adaptations.

1. Check the worktree for existing changes; preserve unrelated work.
2. Fetch Bromax `origin/main` and branch from its updated commit.
3. Keep each PR focused on one issue and its acceptance criteria. Use `perf:`,
   `fix:`, `build:`, `ci:`, `refactor:`, `docs:`, `test:` or `chore:` titles.
4. Fetch/rebase before final validation when the base changed. Recheck affected
   behavior after resolving conflicts.
5. Open the PR with explicit `--repo fabiobove-dr/bromax --base main`. Use the
   [PR template](.github/pull_request_template.md); report checks not run.
6. Squash-merge into Bromax `main` after relevant checks pass, then delete the
   merged feature branch. Never treat missing checks as passing checks.

Follow the user's authorization for publishing and merging; this file does
not grant permission on its own. Do not rewrite published `main` history.

## Scientific and performance constraints

Preserve requested precision, timestep, PME order/grid accuracy, cutoffs,
electrostatics, integrators and other simulation algorithms unless the issue
explicitly authorizes changing them. Faster execution alone does not prove a
correct change. Retain conservative paths for unsupported configurations.

State the required equivalence: bitwise reproducibility, numerical equivalence
within existing test tolerances, or physical/statistical equivalence. They are
different claims. Explain behavior under `-reprod` and checkpoint/restart where
affected; timing-based tuners must not silently override reproducibility.
Do not loosen tolerances just to make an optimization pass.

Before claiming speedups, record baseline/changed commits, workload provenance,
hardware/backend, compiler/build flags, precision, ranks/threads and repeated
end-to-end measurements with noise treatment. Follow the dependency order and
merge gates in [roadmap #33](https://github.com/fabiobove-dr/bromax/issues/33).
GPU/scheduler changes require appropriate hardware validation, not a CPU-only
test pass. Report unavailable hardware as a limitation.

## Code, build and tests

Read callers and feature guards before deleting or changing shared code. Trace
CPU/CUDA/HIP/SYCL/OpenCL, MPI/thread-MPI, single/double precision and affected
simulation features; a locally unused path may still be supported. Prefer
existing utilities and conventions. Add a focused regression test for changed
behavior; documentation-only changes do not need simulation tests.

- [Formatting rules](docs/dev-manual/formatting.rst) and
  [tool commands](docs/dev-manual/code-formatting.rst): clang-format 18.1.8,
  Clang 18 clang-tidy, `.clang-format`, `.clang-tidy` and `.gitattributes`.
  Use `CLANG_FORMAT=clang-format-18 admin/clang-format.sh --rev=<merge-base> check`.
  `admin/clang-tidy.sh` uses a configured compilation database; see the tool
  commands before selecting its build directory and checker invocation.
- [CMake conventions](docs/dev-manual/build-system.rst): use the surrounding
  targets, options and feature guards; do not add a dependency for a few lines.
- [Testing conventions](docs/dev-manual/testutils.rst): reuse the existing
  GoogleTest/testutils and simulation database. Configure `BUILD_TESTING=ON`
  and `GMX_BUILD_UNITTESTS=ON`, build the `tests` target, then run
  `ctest --test-dir <build> --output-on-failure --no-tests=error`.
- Documentation belongs beside the feature or in `docs/`, with user-facing
  limitations and developer invariants updated when behavior changes.

## Task instructions

Read the relevant repository skill when its task applies:

- [Performance](skills/performance/SKILL.md): profiling and measured optimization.
- [PR workflow](skills/pr/SKILL.md): preparing and landing a scoped fork PR.
- [CI](skills/ci/SKILL.md): editing GitHub build/test workflows.
- [C++/CMake](skills/cpp/SKILL.md): compiled code, configuration and test changes.

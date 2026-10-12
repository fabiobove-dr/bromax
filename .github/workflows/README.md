# Bromax continuous integration

All workflows run in `fabiobove-dr/bromax`; they never push to or open PRs
against upstream GROMACS. Tokens have read-only repository permissions and
checkout does not retain credentials. GitHub Actions requires no GitLab
runner, token or project. Feature branches run through `pull_request`; only
`main` runs on `push`, avoiding duplicate push/PR builds for feature branches.
Superseded runs for a PR/ref are cancelled.

## Pull requests and main

`linux.yml` configures, builds the application and all built-in tests, then runs
CTest with GCC 13 and Clang 18 in Release and Debug. Additional GCC Release
configurations exercise thread-MPI disabled, external OpenMPI, and double
precision. CPU jobs use FFTW and SIMD=None for portable coverage; these are
correctness checks, not performance benchmarks. OpenMPI permits local
oversubscription for tests on hosted runners, with binding disabled.

`build_cmake.yml` retains Windows x64/ARM64 and macOS Clang/OpenCL coverage.
Both workflows skip documentation-only changes. Issue #8 tracks the separate
fast formatting/static-analysis gate and stable required-check aggregation.
Until that gate lands, do not require these path-filtered workflows for
documentation-only PRs: GitHub can otherwise leave required checks pending.

Compiler caches are separated by compiler/build mode and CMake configuration.
Linux jobs upload JUnit results, CTest output, configure/build/test logs and
CMake diagnostics for seven days, including failed runs. Windows/macOS jobs
retain CTest and CMake diagnostics.

## Scientific coverage and fixtures

The current source tree supplies unit/integration tests, including simulation
tests. Supplemental regression fixtures are the upstream GROMACS 2026.4
release archive from `https://ftp.gromacs.org/regressiontests/`, verified with
SHA256 by `.github/scripts/fetch-regressiontests.cmake`. Its LGPL license and
provenance remain in the archive. The upstream GitHub regression-test mirror
is stale (2020); it is deliberately not used. Release fixtures are not claimed
to cover every new 2027 development feature. Updating the fixture version and
checksum requires a reviewed PR and compatibility tests.

These checks do not establish GPU correctness, physical/statistical
equivalence, or a performance baseline. Issues #22, #30 and #32 track those
additional guardrails. Do not infer backend validation from a CPU CI pass.

## Manual and scheduled checks

Run `gh workflow run linux.yml --repo fabiobove-dr/bromax` for the full Linux
matrix, Clang ASAN/UBSAN builds and Sphinx documentation build. The same broader
checks run each Monday at 03:23 UTC. Windows/macOS builds can be triggered with
`gh workflow run build_cmake.yml --repo fabiobove-dr/bromax`.

GPU tests require a separately approved hardware runner; no untrusted PR code
is sent to self-hosted machines by these workflows. GitLab-specific files can
be removed under #10 after the retained checks have demonstrated parity.

For local Linux reproduction, use the configure/build/test commands in
`linux.yml`; set the corresponding compiler and configuration values. Run
`actionlint .github/workflows/*.yml` after editing workflows. Check script
download behavior with `cmake -P .github/scripts/fetch-regressiontests.cmake`.

Workflow syntax and concurrency follow the official GitHub documentation:
https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
and https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency.

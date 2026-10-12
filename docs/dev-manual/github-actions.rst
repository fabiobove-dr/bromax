.. _bromax-ci:

Bromax GitHub Actions
=====================

Development and CI run in ``fabiobove-dr/bromax``. No normal build, test,
documentation or PR workflow needs an upstream runner, token or project.
The `Actions page <https://github.com/fabiobove-dr/bromax/actions>`_ records
checks and artifacts; all PRs target this fork.

The control plane and exact commands are documented in
``.github/workflows/README.md``. CPU configurations include GCC/Clang
Release/Debug, thread-MPI on/off, external MPI and double precision.
Windows x64/ARM64 and macOS Clang/OpenCL remain represented. Manual/weekly
checks include Clang ASAN/UBSAN and Sphinx documentation. These configurations
have passed during the GitHub migration; they do not prove GPU or long-run
physical/statistical validation. See :doc:`../user-guide/bromax-performance-accuracy`
for scientific requirements and backend evidence.

PR quality checks precede broad build matrices. The Bromax merge base determines
changed files. Formatting/copyright/Python/workflow checks run first; compiled
changes receive a CPU smoke build and clang-tidy analysis where a compilation
database exists. Documentation-only changes skip irrelevant compiled jobs while
retaining stable gate/result checks. Superseded runs are cancelled. Follow the
current workflow README for exact check names and manual dispatch commands.

JUnit, configure/build/test logs, formatter patches and analysis diagnostics are
retained in run artifacts. Inspect the exact commit and job results; a skipped
backend test does not establish that backend's correctness. GPU/self-hosted work
requires suitable hardware and a separately reviewed execution policy.

Regression fixtures
-------------------

``cmake -S . -B build -DREGRESSIONTEST_DOWNLOAD=ON`` downloads a pinned,
SHA256-verified GROMACS 2026.4 release fixture archive over HTTPS for development
trees. It supplements the current source tree's built-in unit/integration tests;
it is not claimed to cover every new 2027 development feature. Released source
packages retain their version-specific fixture selection. The canonical corpus,
performance policy and physical-validation workflows remain tracked in issues
#32, #9 and #22 until their actual implementations land.

.. _variables:

Build environment
-----------------

``CC``/``CXX`` select compilers, and ``CI_JOB_ID`` indicates a CI run to existing
CMake/test logic. Historical shared scripts in ``admin/ci-scripts/`` retain
caller-supplied environment interfaces; their names do not require a particular
hosting service. Preserve these helpers when migrating a caller and provide
its required build/source paths explicitly.

.. _containers:

Optional local container tooling
--------------------------------

``admin/containers/`` still generates local build recipes. Generated image tags
use the Bromax GHCR namespace; this does not imply those images are published.
Build the required base image locally or supply an image you control. Do not
push images or publish releases without the relevant authorization.

``docs/docs.dockerfile`` accepts a full ``BASE_IMAGE`` reference supplied by the
caller. Documentation can also be built directly with CMake/Sphinx, or retrieved
from the manual GitHub documentation job; no pre-published private CI image is
required by the normal workflow.

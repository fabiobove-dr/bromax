# Immutable CPU benchmark container — preparation only

This is an **opt-in** CPU-only container profile for the existing paired Bromax
benchmark runner (`../paired.py`). It is independent of the current hosted
`.github/workflows/benchmark.yml`; the hosted workflow is not converted to the
container by this change. No timings or simulation results are claimed here.

## Build and freeze the runtime (once)

From a Bromax checkout on a native Linux x86-64 machine with Docker:

```bash
docker build --platform linux/amd64 -f admin/benchmarks/container/Dockerfile \
  -t bromax-bench:cpu-v1 .
docker image inspect -f '{{.Id}}' bromax-bench:cpu-v1
```

Retain the image binary and its full `sha256:...` **image ID**, together with the
build log and source Dockerfile. Rebuilding the Dockerfile later can select new
Ubuntu packages: **a tag or identical Dockerfile alone is not a frozen image**.
For shared distribution, publish the image to a trusted registry and use its
`registry/name@sha256:...` manifest digest instead. This runner **rejects tags**.
The local `sha256:<image ID>` is immutable on one Docker installation; for moving
between machines, push/save and load the identical image, or use a registry digest.

## Prepare independent source trees (no benchmarking during setup)

Create a separate writable workspace with two Git checkouts, not symlinked
copies. Both must have `.git` and the expected Bromax `origin` history:

```text
workspace/
  baseline/    # clean Bromax main checkout; fetch origin/main first
  candidate/   # clean Bromax feature branch checkout
```

`../paired.py` verifies the baseline's fork origin/history, clean tracked trees,
source-to-binary Git SHA, matching compiled settings and canonical corpus hashes.
It refuses a pre-existing `results/` and does not accept upstream GROMACS as
its baseline. Source commit and corpus revision must be recorded independently.

## Launch when the fixed-host benchmarking phase is approved

```bash
python3 admin/benchmarks/container/run.py \
  --workspace /absolute/path/to/workspace \
  --image sha256:<64-hex-image-id> \
  --tag argon --jobs 2 --cpuset 2-3
```

This performs a clean CMake/Ninja Release build of both checkouts **inside the
same image** (GCC/G++ 13, FFTW, mixed precision, CPU-only, thread-MPI,
`GMX_SIMD=SSE2`, two OpenMP threads in the existing runner). The image is native
`linux/amd64` only, never an emulated CPU. It runs available CTest checks before
any timing, then the existing five reversed-order pairs per corpus case. The
entrypoint has no runtime network access; it intentionally disables regression
suite downloads, so passing CTest is **not** a full regression/physical-validation
qualification. The GPU, double-precision, DD and long statistical matrices
require separately validated profiles. Unit tests and the corpus integrity
checks execute before building the candidate. Build and test failures stop the
pipeline; no timings should be interpreted if they occur.

`workspace/artifacts/` contains host kernel, immutable image reference/ID,
CPU affinity, selected cpuset, toolchain package versions and compile logs.
`workspace/results/` contains `results.json`, `summary.md`, raw simulation
logs and all existing paired-runner provenance. Both directories must be absent
before starting. An unsuccessful attempt retains diagnostics; use a fresh
workspace to retry. `--cpuset` must select real CPUs available to Docker on the
host, otherwise Docker correctly refuses to start.

## Scientific and comparability limitations

A container fixes the *userspace and build toolchain*, **not** the CPU model,
microcode, kernel, container runtime, CPU frequency/governor, NUMA topology,
thermals, memory bandwidth or host interference. The same image can produce
different performance or floating-point trajectories across hosts. Compare
**baseline/candidate pairs on the same machine**, with identical CPU affinity,
compiler, settings and physical input. Use the same hardware class and recorded
kernel/driver/clock state for longitudinal comparisons. A speedup on one CPU
cannot be claimed for all CPUs.

This v1 profile uses common SSE2 instead of CPU-dependent `SIMD=Auto` to hold
one relevant code-generation choice fixed. It does not model best-possible
performance on every processor; add a separately identified AVX2/AVX-512/GPU
profile when required and never pool their results. Canonical corpus v1 is
small and **does not validate biomolecular, FEP, DD or multi-GPU claims**.

Scientific rigor also requires separate validation: force/energy/virial
comparisons, energy drift, integrator convergence and (for long MD) ensemble
statistics. Match the physical model, not just atom count and number of steps.
Use #22/#30/#46 gates before attributing a speedup to a numerical change.

A future comparison with **GROMACS 2026.4** (stable reference as of 2026-11-12)
must be a separate, carefully qualified protocol. The current paired runner is
*deliberately* Bromax-main vs Bromax-candidate only, and its fork-origin guard
must not be relaxed to permit unsupported cross-version claims. Validate
cross-version TPR/MDP compatibility, default settings, trajectories, and
statistical equivalence before treating throughput ratios as meaningful.

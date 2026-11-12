# Bromax scientific development and benchmarking handoff

*Operational plan, recorded 2026-11-12. Issue/PR statuses below are a snapshot;
consult GitHub for current checks and reviews.*

## Objective and success definition

Bromax is an independently maintained GROMACS-derived molecular-dynamics engine.
Improve accuracy **where a genuine numerical/physical defect is demonstrated**,
repeatability and computational throughput without changing the requested
model to manufacture speedups. Preserve precision, integrator/timestep, force
field, topology, cutoffs, PME error settings, constraints and ensemble definitions.
Statistical ensemble equivalence is not the same as trajectory bitwise identity.

A Docker image pins the userspace/toolchain **only**. The host CPU, GPU, driver,
kernel, clocks, power/thermals and memory bandwidth still affect results.
Scientific tests may run in GitHub CI. **Performance comparisons and associated
optimization acceptance decisions are deferred to a declared fixed host with
an immutable Docker image ID/digest.** Do not make numerical speedup claims from
hosted GitHub runners, small microbenchmarks or builds alone.

## Dependency and execution queue

| Priority | Issues / work | Work permitted before benchmarking | Merge gate |
| --- | --- | --- | --- |
| 0 | #46, PR #47 | Scalar CPU Verlet-buffer correctness; #47 merged, explicit 1x1 issue remains | Correct numerical tests, physical checks, unaffected backends |
| 1 | #30, PR #45 | CPU repeat/restart CI; complete missing GPU/DD/precision coverage incrementally | Deterministic outputs for declared fixed paths; CI, no false universal reproducibility |
| 1 | #22, PR #52 | Fast canonical NVE integrator checks; longer NVT/NPT ensemble and kinetic distribution **only after statistical calibration** | Scientific tests with original tolerance and raw evidence |
| 1 | #48 | Triage inherited project-header Clang-Tidy findings; avoid vendored code/style mass changes | Changed-source gate and relevant tests |
| 1 | #49, PR #50 | Immutable CPU Docker image/toolchain and short MD run proof, no paired timing | Image build, native MD smoke, CI; benchmarks deferred |
| 1 | #13 | Source/backend reachability and build-matrix inventory; proven dead code only | Backend-aware build and unit coverage; any build-time claims deferred |
| 2 | #28 | Core autotuning API, mock candidates, timeout, -reprod/fallback unit tests **without selecting faster kernels** | No model changes, bounded calibration, reproducibility tests |
| 2 | #29 and #27 | Document readiness/ownership; behavior-neutral API refactor behind existing paths | CPU/GPU-specific CTests; GPU scheduling remains gated |
| 2 | #20 and #21 | ED shift and mixed PME correctness diagnosis and focused tests | PBC/DD/GPU-specific force/energy references as applicable |
| 3 | #1-5, #14-19, #23, #25-26 | Isolate hypotheses, add logging/coverage while preserving defaults | **Do not merge speedup/default selection until controlled local paired measurements** |
| 3 | #44 | Independent cuFFT reset reproducer across supported toolkits | CUDA hardware/sanitizer; attribution evidence, no suppression |
| Local | #51 | Published biomolecular workload provenance and GROMACS stable comparator protocol | Physically equivalent systems, published inputs, fixed-host repeats |

Use [roadmap #33](https://github.com/fabiobove-dr/bromax/issues/33)
for the full dependency graph. Independent correctness/documentation fixes can
proceed in parallel; do not bypass #28/#29 with ad-hoc tuners or synchronization.

## Change and merge discipline

1. Inspect `AGENTS.md`, existing PRs, main/head SHA, and issue acceptance
   criteria. Do not overwrite user changes or upstream GROMACS.
2. Branch only from current fork `main`. One issue/scope per PR; avoid
   mixing numerical, CI, and performance changes.
3. Classify the required equivalence:
   **bitwise on a declared supported layout**, **numerical within unchanged
   tolerances**, or **physical/statistical with stated tests and uncertainty**.
4. Add regression tests that fail on the old behavior, where feasible.
   Preserve conservative paths, `-reprod` semantics, and checkpoint continuity.
5. For correctness/CI-only changes, validate the actual configuration in
   GitHub CI. No claims from queued, cancelled, skipped or failed jobs.
6. For performance changes, stop at a reviewable PR pending the fixed-machine
   benchmark. Record the exact proposed host profile, hardware, corpus, binary
   hashes and scientific outputs required for sign-off.
7. Squash-merge to **this fork only**, only when applicable gates pass. Close
   a GitHub issue as completed only when its acceptance criteria are met;
   close a false-premise issue as *not planned* with source evidence.

## Dedicated-host benchmark handoff (future stage)

- Prepare clean Bromax baseline and candidate checkouts and a **separate**
  pinned stable GROMACS baseline for #51.
- Build and retain a Docker image with immutable image ID or registry digest;
  retain source SHA, flags, compiler, precision, driver, CPU/GPU IDs, kernel,
  affinity and clock/thermal policy. Never pool SSE2/AVX2/GPU profiles.
- Check corpus integrity, resolved input physical settings and numerical/
  statistical validation **before** timing. Follow #32 and #22/#30.
- Compare baseline/candidate in alternating paired order on the same declared
  machine. Repeated runs and uncertainty; report complete trajectories,
  memory/power only if measured, ns/day and end-to-end wall time.
- Compare Bromax incremental improvements separately from absolute GROMACS
  stable-release competitiveness. Version differences must not be credited to
  Bromax optimizations without attribution.

The previous GitHub-hosted `benchmark.yml` is now manual-only and exploratory;
no scheduled or PR-triggered speed comparisons run by default. It remains
available for diagnostics and is **not** a substitute for this local stage.

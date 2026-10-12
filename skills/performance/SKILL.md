---
name: performance
description: Profile and optimize Bromax simulation or build performance with numerical validation and reproducible measurements.
---

Read root `AGENTS.md` for repository and scientific invariants.

1. Read the linked issue's dependencies and merge gate before choosing a hot
   path. Use existing timers/benchmarks, including the nonbonded benchmark under
   `src/gromacs/nbnxm/benchmark/`; inspect its callers before reusing it.
2. Measure the current bottleneck and state a falsifiable hypothesis. Keep the
   baseline build and input configuration available for comparison.
3. Make the smallest change that addresses that bottleneck. Candidate algorithms
   must already be legal for the requested physics; reuse shared tuning/readiness
   infrastructure instead of adding another timing or event system.
4. Run targeted numerical tests first, then repeated end-to-end benchmarks.
   Include warm-up, sample counts, noise, overhead and regressions across the
   affected workloads. A microkernel improvement is not an end-to-end claim.
5. Keep the fallback when calibration is inconclusive. If required GPU/backend
   evidence is unavailable, prepare a reviewable PR and report the unmet gate;
   do not claim validation or merge a default-changing optimization.

The canonical corpus and benchmark policy are tracked in issues #32/#9; inspect
their actual implementation status rather than assuming they already exist.

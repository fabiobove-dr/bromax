# Canonical integrator convergence in GitHub CI

This is **scientific validation**, not a performance benchmark. The physical
validation workflow uses the existing checksummed corpus v1 and inherited
GROMACS `physical_validation` test definitions without shortening integration
duration, tuning tolerances, or updating references.

The first, deterministic PR check selects only the canonical NVE water
integrator-convergence test with `--tag integrator --physical-validation`.
The source MDP, topology and initial coordinates are unchanged. The
`-n 3 -t 0.25` convergence requirement comes from the original suite.
Its durations are 1000/2000/4000/8000 integration steps at successively
halved timesteps, so results are **not** evidence of long-time ensemble
accuracy or throughput improvement.

Run it manually with
[the workflow](../../.github/workflows/physical-validation.yml) or allow
the workflow to run on PRs affecting MD numeric algorithms, canonical inputs
or this workflow. Fixed Python 3.11 and NumPy/SciPy/PyMBAR versions support
the inherited physical-analysis code; the C++ test executable is GCC 13
Release, CPU-only, single-rank, mixed precision, SSE2. Outputs and full
build/analysis logs are retained on failures for 14 days.

This workflow does not replace upstream GROMACS regression CTests, Bromax
`-reprod`/checkpoint checks, or the later fixed-machine benchmark protocol.
It currently tests **only** one NVE integrator case. Issue #22 remains open
for NVT/NPT ensemble and kinetic-energy validation, statistically qualified
replicates, double precision, domain decomposition and GPUs. Do not make
stochastic validation an obligatory PR gate until its rejection rate and
confidence procedures have been independently characterized.

Reproduce locally using the same toolchain and package pins (or equivalent
recorded versions), a clean Bromax checkout, and the commands in the workflow.
The GitHub-hosted CPU model is **not fixed**, so no comparative timing
information should be inferred from this job.

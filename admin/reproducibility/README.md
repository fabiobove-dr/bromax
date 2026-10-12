# CPU repeat and checkpoint checks

Run from a clean fork checkout with its matching CPU, mixed-precision executable:

```sh
python3 -m unittest discover -s admin/reproducibility
python3 admin/reproducibility/cpu.py --build build --output reproducibility
```

The runner reuses the canonical, checksummed corpus and benchmark helpers for
build provenance and subprocess handling. It rejects dirty tracked sources,
stale executables, GPU builds, double precision, and existing output directories.
The CI calls it in GCC and Clang Release/thread-MPI jobs after ordinary CTest.
Linux and quality workflow steps explicitly use Bash with pipeline failure
propagation, so a failing compiler/test cannot be hidden by `tee` logs. Clang
OpenMP development headers are explicitly installed.

Each of the three corpus cases runs at one rank with one and two OpenMP threads.
Within each configuration, two independent 200-step `-reprod` runs and a
100-step run followed by an appended checkpoint restart to step 200 must have
identical nonempty TRR and EDR SHA256 hashes. Comparisons are within each layout;
one-thread results are not compared against two-thread results. CPU work is
explicit, and inherited `OMP_NUM_THREADS` is removed from child processes in
favor of explicit `-ntomp`. There is no wall-time stopping condition.

Working MDPs change only duration, output intervals (every ten steps), and the
first recorded corpus validation seed for `ld-seed` and `gen-seed`. They retain
the input timestep, interactions, cutoffs, precision and coupling algorithms.
These are short repeat/restart checks, not the corpus's long physical-validation
runs or performance measurements. No statistical threshold is changed.

Artifacts contain source/executable provenance, build cache, corpus checksum,
resolved MDP, processed topology, TPR/checkpoints, raw TRR/EDR and logs, commands,
output hashes, and a JSON/Markdown result even after a caught setup/run failure.
Normal CI retains them for seven days. Missing, empty or unequal files fail;
outputs are never silently overwritten. A restart appends only after mdrun
validates the checkpoint and existing output files.

GPU, multi-rank/DD, external MPI, double precision, changing compiler/hardware,
signal-driven stopping and other integrators/features are outside this check.
See the user performance guide for the adaptive-choice audit and equivalence
tiers. This representative coverage does not close all of issue #30.

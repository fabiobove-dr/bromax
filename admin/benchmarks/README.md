# Paired performance benchmarking

`benchmark.yml` compares a recorded Bromax `main` baseline with a candidate
from this fork, using canonical corpus v1 (#32). It is manual and weekly;
performance outcomes are not required PR failures. PRs changing this benchmark
framework itself run the argon case to exercise the pipeline before merge. Both revisions build on the
same ubuntu-24.04 runner using GCC 13, Release, FFTW, SIMD=Auto, single/mixed
precision, CPU-only thread-MPI and identical options. Hosted CPU models can
vary between runs: compare pairs within one run and group historical variance
by recorded hardware/toolchain, not just the runner label.

After merge:

```sh
gh workflow run benchmark.yml --repo fabiobove-dr/bromax \
  -f candidate=<commit-or-branch> -f tag=argon
```

Empty candidate uses the workflow commit; `tag=cpu` selects all cases. Repeat
a same-commit run to characterize noise. Baseline always checks out this fork's
main; the runner requires its SHA to be reachable from `origin/main`, clean
tracked sources and executable SHA matching the source checkout. This also
prevents stale local binaries from being credited to a newer commit.

## Execution and scientific guards

The standard-library runner reuses corpus integrity/tag selection, then runs
CTest on both builds with existing unit/integration/regression tolerances.
Failure blocks timing and retains logs/JUnit. GPU labels in CPU CTest output
do not imply execution on GPU hardware. Long ensemble/kinetic/physical tests
remain #22; their absence is explicit in the summary, not presented as a pass.

Each case generates a working MDP with the corpus's duration and fixed random
seeds, preserving all other settings and original velocities. Both sides'
resolved MDP, processed topology and TPR physics dump must match. Comparison
ignores only MDP/topology comments and the dump's version/path banner; numerical
values/defaults, grids, topology, coordinates and velocities remain compared.
A legitimate change to these representations must be reviewed, not accepted by
weakening this guard. PME tuning is disabled (`-notunepme`) for comparable grids
and cutoffs. CPU kernels, one thread-MPI rank, two OpenMP threads and pinning are
explicit; automatic timing-based resource division is not part of this test.

Run five baseline/candidate pairs, reversing order on alternating pairs.
`-resetstep 1000` excludes warm-up from GROMACS counters within each 6000-step
process. The log must confirm reset. Report ms/step and ns/day from the counters;
separately record total process wall time including startup. Raw logs retain
wall-cycle counters and outputs. JSON contains each pair/order, commands,
metadata, input/TPR/executable hashes and available sysfs frequency, temperature
and power snapshots. Unreadable counters are unavailable; clocks/thermals are
not controlled on hosted runners. Copy full CMake caches, resolved parameters,
processed topologies and energy/log outputs into the artifact.

## Exploratory comparison

Use paired log(candidate ms/step / baseline ms/step). Report the geometric mean
time ratio and a Student-t 95% interval (five pairs, four degrees of freedom).
Labels are improvement if the entire interval is below 1, regression if above
1, and indistinguishable/noise otherwise. This assumes approximately normal,
independent paired log differences. Five observations cannot establish that
assumption or calibrate every hosted runner. Timing quantization and zero
observed variance do not establish reproducibility. Labels are exploratory,
not scientific equivalence or automatic PR rejection. Establish per-hardware
historical variance before introducing required thresholds (#9).

No accuracy setting or tolerance is relaxed to obtain a faster result.
Benchmark timing is separate from the corpus's longer scientific runs.

## Local reproduction and extension

Build two clean source checkouts with the same flags, including `all tests`
and the native pinned regression fixtures. Run:

```sh
python3 -m unittest discover -s admin/benchmarks
python3 admin/benchmarks/paired.py \
  --baseline /path/to/main --baseline-build /path/to/main/build \
  --candidate /path/to/candidate --candidate-build /path/to/candidate/build \
  --tag argon --output /path/to/new-results
```

Output must be a new directory; existing results are never overwritten.
`results.json` and `summary.md` are also written for failures after setup, with
partial pairs explicitly incomplete. GitHub uploads results/build/test logs on
success or failure and retains artifacts for 30 days. Historical comparisons
must download/retain the artifacts before expiry.

A separately approved GPU runner can extend the workflow's runner/backend/GPU
matrix without replacing its paired build/test/report/artifact phases. First
qualify GPU cases and tolerances in the corpus, then extend CPU-only build
validation and the centralized launch arguments/metadata in `paired.py`.
Trustworthy multi-stream stage timings require #25; do not send untrusted PR
code to self-hosted runners. V1 makes no GPU-performance claim.

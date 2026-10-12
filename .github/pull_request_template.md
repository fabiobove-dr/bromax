## Issue and scope

Closes #<!-- issue number -->

Describe the problem, resulting behavior and reason for this change.

## Correctness and validation

- Tests/checks run and their results (state any checks not run):
- For simulation changes: physical/numerical invariants, comparison tolerances
  and evidence from existing validation tests:
- Equivalence required: bitwise, numerical or physical/statistical; behavior
  under `-reprod` and checkpoint/restart where affected:

## Performance

For `perf:` changes, include the baseline and changed commits, workload/input
version, hardware, build options, precision and rank/thread layout. Report
repeated end-to-end before/after measurements and noise/confidence treatment.
For other changes, write N/A.

## Compatibility and fallback

List affected CPU/GPU backends, single/double precision, MPI/thread-MPI and
simulation features. Explain unsupported configurations, fallback behavior and
how the selected path can be diagnosed from logs, where applicable.

## Merge checklist

- [ ] This PR targets `main` in `fabiobove-dr/bromax`.
- [ ] The change is scoped to one issue and relevant checks pass.
- [ ] Scientific and performance evidence is included where applicable.
- [ ] Squash-merge into Bromax after validation; upstream GROMACS is read/fetch-only.

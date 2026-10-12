# Canonical CPU corpus v1

This corpus gives #9 (paired performance runs) and #22 (physical validation)
the same checksummed systems. It reuses inherited GROMACS inputs already in
`tests/physicalvalidation/systems/`, under the repository's LGPL-2.1-or-later
license (`COPYING`). Preserve the original topology citations, including the
argon Lennard-Jones parameter reference. `corpus.json` records source revision,
SHA256 of every coordinate/topology/MDP input, purpose, tags and permitted matrix.
The selected topologies are self-contained: no external force-field includes.

| Case | Purpose | Scientific run |
| --- | --- | --- |
| `int_water_md_none_pme_pme` | 2700 atoms, flexible water, NVE, electrostatic and LJ PME | Original 1000 steps at 0.0005 ps, then 2000/4000/8000 steps with successive timestep halving; existing integrator tolerance 0.25 |
| `ens_water_md_settle_pme_vr` | 2700 atoms, SETTLE, electrostatic PME, NVT | 500000 steps at 0.002 ps per temperature state; ensemble and kinetic-energy checks |
| `ens_argon_md_pme_vr_cr` | 1000 neutral atoms, CPU nonbonded work, NPT | 500000 steps at 0.002 ps per temperature/pressure state; ensemble and kinetic-energy checks |

The argon case's historical name includes `pme`, but its MDP does not request
electrostatic PME. Do not classify workloads from names. V1 permits CPU,
single precision, one rank, using serial or thread-MPI builds. Record thread
count explicitly. GPU, double precision, DD, virtual sites, FEP, biomolecules and
large PME-dominated systems need separate qualified cases/matrix extensions;
these small systems cannot represent their performance. V1 is an input contract,
not evidence that long statistical runs or those additional regimes have passed.

## Selection and integrity

From the repository root:

```sh
python3 -m unittest discover -s tests/corpus
python3 tests/corpus/check.py --tag cpu > selected-corpus.json
python3 tests/corpus/check.py --tag ensemble --tag settle --physical-validation > selected-systems.json
```

Repeated tags intersect (all requested tags must match); an empty selection
fails. The second form emits the existing physical-validation suite's JSON
format, suitable for `tests/physicalvalidation/gmx_physicalvalidation.py`. That
runner reads inputs from `systems/` beside its own script; use `--wd` for the
output directory. No consumer should embed another input corpus
in workflow YAML. The checker validates all corpus inputs before selection and
rejects changes to the inherited validation definitions or input checksums.

Changing an input, scientific definition, duration, seed policy or allowed
matrix requires a reviewed corpus-version change. Do not silently update hashes
to keep results comparable. Retain the old manifest and input revision in the
result artifacts; git history supplies the immutable previous version.

## Benchmark contract

Each case uses 1000 warm-up steps followed by 5000 measured steps and five paired
baseline/candidate samples. Generate a working MDP with total `nsteps=6000` and,
for stochastic coupling, `ld-seed=20261012`; preserve every other simulation
setting and initial velocity. Use `mdrun -resetstep 1000` to reset timing after
warm-up in the same process. This duration is separate from scientific runs;
do not shorten statistical validation to the timing window. Alternate the run
order within pairs on the same hardware/toolchain and resource layout. Baseline
is a recorded Bromax `main` SHA. Report both individual samples and uncertainty;
do not assert speedup from startup-dominated timings or impose a required
regression threshold before runner variance is known (#9).

## Scientific contract

Use each case's unchanged `validation` definition and original MDP durations.
The integrator test compares energy-fluctuation convergence under timestep
halving, with the inherited relative tolerance 0.25. Ensemble comparisons use
the inherited four-standard-deviation limit and temperature/pressure offsets;
kinetic-energy distribution checks use the inherited 0.01 significance level.
These are different tests, not a universal force/energy/virial tolerance.
No force, virial or drift reference is qualified by this initial corpus.

For stochastic scheduled replicates use the five `validation_ld_seeds` in the
manifest, applied to generated working MDPs, and retain those MDPs. Record any
other random seed supplied by a consumer; do not leave automatic seeds
unrecorded. Statistical rejection can occur for a correct simulation: the
0.01 test has a nominal 1% false-rejection rate for one correctly calibrated
comparison; multiple correlated tests do not share one global 1% rate. Ensemble
limits depend on estimated uncertainty and correlated samples. Record sample
length, seed, every statistic and threshold. Characterize observed variance
before making these checks required on PRs (#22). An input/100-step smoke pass
does not establish ensemble correctness.

## Required result metadata

Every #9/#22 result must retain:

- Corpus version, manifest/input checksums, tags and selected case; baseline and
  candidate commit SHAs and dirty-state flags.
- Compiler/version, CMake cache/build flags, executable version/hash, precision,
  backend, CPU/GPU models, driver/runtime and MPI implementation. For scientific
  analysis, also record Python, NumPy, SciPy and PyMBAR versions.
- Rank/OpenMP thread layout, affinity and all grompp/mdrun commands; resolved
  MDP (`mdout.mdp`), processed topology (`grompp -pp`) and generated TPR hash,
  including defaults omitted by the source MDP and duration/seed overrides.
- Warm-up/sample counts, paired order, individual timings, uncertainty,
  validation statistics/thresholds/seeds and logs/energies needed to diagnose
  failure. Thermal, clock and power data when obtainable; explicit `unavailable`
  with reason otherwise.

#9 owns execution/comparison/reporting; #22 owns scientific CI. This PR defines
their shared inputs and selection, without adding another simulation runner.

.. _bromax-performance-accuracy:

Bromax performance and accuracy contract
========================================

Bromax is an independently maintained GROMACS fork. Faster execution is useful
only when the requested simulation remains scientifically valid. This guide
separates execution choices from accuracy and model choices; it does not replace
the detailed :doc:`mdrun-performance`, :doc:`mdp-options` or :doc:`validation`
guides.

What an optimization changes
----------------------------

Implementation changes such as removing unused compiled code, caching an
unchanged execution graph, or eliminating a demonstrably redundant wait are
intended to preserve the calculation. Their dependencies, resource lifetimes
and supported configurations still need tests.

Equivalent kernel selection, CPU/GPU placement and parallel reduction ordering
can change floating-point rounding while implementing the same equations.
Validate forces, energies and virials with the existing test tolerances for the
affected algorithm and precision. Do not demand bitwise identity from a path
that deliberately changes reduction order, or call statistical agreement proof
of a correct force calculation.

Accuracy-bound tuning changes discretization or approximation choices while
preserving a declared bound. PME grid planning and Verlet buffer/list tuning
belong here when their accuracy constraints remain enforced. They need an
explicit bound and validation, rather than a blanket claim of equivalence.

Changes to the force field, electrostatics formulation, integrator, timestep,
coupling algorithm or precision are scientific/numerical configuration changes.
They must be authorized and assessed separately from implementation speedups.

Options that affect accuracy
----------------------------

.. list-table:: Accuracy-sensitive choices
   :header-rows: 1
   :widths: 30 70

   * - Choice
     - Consequence and required check
   * - ``dt``, integrator, multiple time stepping
     - Change integration error, stability and sampling. Keep them fixed in an
       implementation benchmark; validate a changed integration scheme separately.
   * - ``constraints``, ``lincs-order``, ``lincs-iter``, ``lincs-warnangle``
     - Constraint choices and solver settings affect accuracy/stability;
       ``lincs-warnangle`` controls diagnostics, not solver accuracy. Larger
       timesteps are not automatically justified by enabling constraints.
   * - ``fourierspacing``, PME order, explicit Fourier grid, ``ewald-rtol``
     - Affect reciprocal/direct-space electrostatic accuracy. A faster FFT grid
       must still satisfy the requested accuracy; changing these inputs is not
       an unchanged-physics kernel optimization.
   * - ``rcoulomb``, ``rvdw``, interaction modifiers and potential formulation
     - Can change interactions or their approximation. Keep the requested model
       and its error constraints fixed when comparing execution implementations.
   * - ``nstlist``, ``rlist``, ``verlet-buffer-tolerance``
     - List lifetime and buffer size interact. With automatic Verlet buffering,
       increasing list lifetime requires a corresponding buffer to maintain the
       configured energy-drift tolerance. Disabling automatic buffering or
       shrinking the list without validation can miss interactions.
   * - ``nstcalcenergy``, coupling intervals and output intervals
     - Affect observable availability, coupling behavior or I/O cost. Record all
       intervals in benchmarks; changing the requested sampling/coupling schedule
       is not a free implementation optimization.
   * - Mixed versus double precision
     - Changes arithmetic accuracy and throughput. Compare like precision with
       like precision; a double CPU pass does not validate GPU double precision.

Use :doc:`floating-point` and the algorithm-specific numerical tests to select
tolerances. There is no universal tolerance that proves all algorithms correct.

CPU/GPU placement, PME and communication
----------------------------------------

GPU offload can accelerate kernels yet lose time to transfers, host waits,
small launches or rank communication. GPU-resident runs keep supported update,
constraint and force operations on the device; inspect the actual task mapping
and timing breakdown in ``md.log``. A GPU-utilization percentage alone does not
identify the end-to-end bottleneck.

``-nb``, ``-pme``, ``-pmefft``, ``-bonded`` and ``-update`` select execution
placement, subject to backend and simulation-feature restrictions.
``-pme auto`` selects a compatible GPU where legal; ``-pme gpu`` requires a
supported GPU/configuration. GPU PME normally performs FFTs on the GPU;
``-pmefft cpu`` is an alternative where supported. Record the selected FFT
library and placement, rather than assuming that a GPU always wins. Compare
alternatives when timing shows an imbalance, holding the scientific inputs
fixed. Relevant hardware/software includes system size, grid shape, CPU/GPU
models, interconnect, driver/runtime, FFT library and rank/thread affinity.

Automatic PP/PME load balancing can exchange direct-space and mesh work by
adjusting cutoff/grid choices within its constraints. This is accuracy-bound
tuning, distinct from keeping every numerical parameter fixed. Record whether
it is enabled and what the run selected.

Domain decomposition and additional PME ranks can improve scaling but alter
communication and reduction order. Do not infer multi-rank, multi-GPU or
cross-node validation from a single-rank result. GPU PME decomposition is an
opt-in path documented as lacking substantial testing in
:doc:`environment-variables`; CUDA/SYCL support is not a Bromax validation claim.

Reproducibility and restart
---------------------------

Distinguish three claims:

* Bitwise reproducibility under the same executable, inputs, supported execution
  path and hardware. ``-reprod`` restricts adaptive optimizations; it cannot make
  every inherently nondeterministic GPU algorithm bitwise reproducible or make
  different compilers/hardware identical.
* Numerical equivalence of forces/energies/virials within declared tolerances.
* Physical/statistical equivalence of ensemble or long-run observables, tested
  with an appropriate statistical method and sampling length.

Each claim requires its own evidence. Timing-based tuning must respect
``-reprod``; checkpoint/restart behavior also needs tests when changing state,
algorithm selection or ownership. Consult :doc:`mdrun-features` and
:doc:`managing-simulations` for inherited execution/restart behavior. Issue
`#30 <https://github.com/fabiobove-dr/bromax/issues/30>`_ tracks remaining coverage.

CPU repeat/restart checks now run in the GCC and Clang Release/thread-MPI GitHub
jobs. For each canonical NVE water, NVT water and NPT argon case, one rank with
one or two OpenMP threads performs two 200-step ``-reprod`` runs and a run stopped
at step 100 and resumed from its checkpoint with ``-append``. Nonempty TRR
(coordinates, velocities and forces) and EDR files must match byte for byte
within each configuration. Output is sampled every ten steps; the first corpus
validation seed is recorded explicitly. These short runs test repeat/restart
consistency, not ensemble correctness. Raw outputs, inputs, commands, build
provenance and comparison hashes are retained as CI artifacts for seven days.
The runner is ``admin/reproducibility/cpu.py``; its README gives local commands.

The current adaptive-choice audit distinguishes these paths:

* PME load balancing: ``pmeTuningIsSupported`` rejects reproducible mode before
  timing-based tuning can run (``ewald/pme_load_balancing.cpp``).
* Domain-decomposition load balancing: ``domdec.cpp`` disables automatic DLB
  in reproducible mode and rejects an incompatible explicit request. The
  one-rank corpus check does not exercise DD or separate PME ranks.
* CPU FFT planning: ``parallel_3dfft.cpp`` supplies ``FFT5D_NOMEASURE`` for
  reproducible mode, avoiding timing-based planning.
* Rank/thread division: ``taskassignment/resourcedivision.cpp`` currently uses
  hardware/size heuristics, not measured startup timings. Fix rank/thread
  counts explicitly when comparing runs, including restarts.
* Verlet list lifetime/pruning: ``nbnxm/pairlist_tuning.cpp`` currently uses
  input/error estimates and fixed backend constants. Dynamic pruning does not
  mean timing-based autotuning; the proposed measured tuner must add an explicit
  reproducible-mode guard or deterministic selection before it is enabled.

New timing-based tuners require a test demonstrating their disabled or
measurement-independent selection under ``-reprod``, in addition to repeated
simulation checks. The PR template and root ``AGENTS.md`` require the declared
equivalence tier and restart behavior. No new tuner is enabled by these checks.

A checkpoint is a continuation of simulation state, including stochastic state;
keep executable, inputs, precision, backend and rank/thread layout fixed for a
bitwise comparison. Logs and checkpoint files contain execution metadata and
are not themselves required to be byte-identical. Changed layout, compiler or
hardware needs separately justified numerical/physical comparison. Existing
feature-specific restart restrictions still apply, including the legacy
expanded-ensemble limitation in :doc:`known-issues`.

GPU kernels that accumulate with unordered floating-point atomics, such as PME
charge spreading, can produce different rounding across launches. ``-reprod``
does not make these paths bitwise deterministic. CUDA Graph capture preserves
dependencies but does not establish deterministic reduction order. The CPU
check supplies no GPU, multi-GPU/DD, external-MPI or double-precision guarantee;
those paths require their own supported-tier validation.

Reproducible performance measurements
-------------------------------------

Use the same immutable topology, coordinates, MDP and starting state for both
versions. Record input checksums/provenance, baseline and changed commits,
compiler/build flags, precision, CPU/GPU, driver/runtime, FFT/MPI libraries,
rank/thread layout and affinity. Record clocks, power/thermal conditions when
available, and avoid competing workloads.

Choose a warm-up long enough for allocation, tuning and thermal transients, then
a measurement interval long enough to distinguish the effect from noise. As a
starting protocol, use 2,000 warm-up steps and 10,000 measured steps for at least
five fresh repetitions per version, alternating versions. Adjust these counts
for the workload and document the final protocol; they are not a universal
confidence guarantee. Use a separate, scientifically appropriate longer run
for physical validation.

For a CPU thread-MPI PME benchmark, an example fresh repetition is::

    gmx_binary=/absolute/path/to/baseline-or-changed/bin/gmx
    input_tpr=/absolute/path/to/immutable/case.tpr
    run_dir=$(mktemp -d)
    (cd "$run_dir" && "$gmx_binary" mdrun -s "$input_tpr" \
        -deffnm benchmark -nsteps 12000 -resetstep 2000 \
        -ntmpi 1 -ntomp 2 -nb cpu -pme cpu)

``-resetstep`` is a developer option shown by ``mdrun -hidden -h``; it resets
timing counters after warm-up. Check the log's reset and measured interval.
Keep each repetition in a fresh directory to avoid an unintended checkpoint
restart. For external MPI/GPU workloads use the appropriate legal invocation
and record it; do not copy the CPU placement flags into a GPU benchmark.

Report repeated end-to-end ``ms/step``, sample counts and dispersion/confidence,
with startup/calibration overhead separately visible. Preserve logs and input
metadata; do not report only the best repetition or a kernel timer. With
``dt`` in picoseconds, ``ns/day = 86400 * dt / (ms/step)``. Increasing ``dt`` can
raise ``ns/day`` without reducing execution time per step, which is why both
metrics and the unchanged timestep matter.

Backend/feature evidence
------------------------

This is a dated Bromax evidence snapshot (2026-10-12), not a support promise for
every inherited GROMACS configuration. Update it with links to the exact
validated commit, workload and results when backend/feature evidence changes.

.. list-table:: Validation status
   :header-rows: 1
   :widths: 25 35 40

   * - Configuration
     - Evidence
     - Limits / status
   * - CPU mixed precision, thread-MPI/serial
     - Local SIMD=None and SIMD=Auto application/test builds passed 107/107 CTest
       entries. Seven Linux configurations passed in
       `PR #42 CI <https://github.com/fabiobove-dr/bromax/actions/runs/38234369276>`_.
     - Tests use the source tree and supplemental 2026.4 fixtures. ISA and
       statistical coverage is limited to the recorded configurations/cases.
   * - CPU external MPI, double precision
     - GCC external-MPI and double-precision jobs passed in PR #42 CI, after
       earlier migration runs in PR #35/#39/#41.
     - Hosted local MPI tests do not establish cross-node scaling/correctness.
   * - CUDA
     - Local commit ``89403261eba81410701a89303b4ac7f051bbc2f9``: CUDA 13.0.48,
       GCC 13.3, RTX 4070 Laptop (SM89, 8 GB), driver 580.173.02, Release,
       SIMD=Auto, mixed precision, CPU FFTPACK/GPU cuFFT. Quick GPU tests passed
       29/29 CTest entries; full CUDA build passed 107/107. GPU cases executed.
     - Single-device evidence; unsupported GTest subcases remain skipped.
       Ten-step memcheck reports a 6,967,984-byte cuFFT allocation at context
       reset, reproduced independently with plan/create/destroy/reset calls.
       Memory-check qualification remains unresolved. No multi-GPU claim.
   * - GPU-resident water / CUDA Graphs
     - On that CUDA build, rigid NVT water ran with GPU nonbonded, PME and
       updates. A 1000-step graph-eligible run recorded 740 MD Graph launches.
     - Short execution evidence; GPU ensemble statistics and all graph step
       signatures are not qualified by this run.
   * - CPU physical validation
     - Same commit, one rank/two threads: flexible-water NVE convergence passed
       (maximum deviation 0.027 versus inherited 0.25). Argon NPT ran four
       500000-step states with seed 20261012; all ensemble comparisons passed
       the inherited four-quantile limit. Kinetic test p=0.518044, alpha=0.01.
     - One seed, specific water/argon cases. More replicates and variance
       characterization are required before statistical tests become PR gates.
   * - SYCL / HIP
     - Inherited implementations; no Bromax hardware results recorded here.
     - Unverified for fork changes; CPU passes provide no backend evidence.
   * - OpenCL
     - Hosted macOS Clang/OpenCL build/test jobs passed in PR #42 CI.
     - This does not qualify other vendors or imply CUDA/SYCL/HIP feature parity.
   * - DD / GPU PME decomposition
     - CPU built-in tests exercise supported multi-rank paths. GPU PME decomposition
       is opt-in and explicitly lacks substantial testing in inherited docs.
     - No Bromax multi-GPU or cross-node GPU validation recorded here.

Reproduce the local CUDA build with ``GMX_GPU=CUDA``,
``CUDAToolkit_ROOT=/usr/local/cuda-13.0``,
``CMAKE_CUDA_COMPILER=/usr/local/cuda-13.0/bin/nvcc``,
``CMAKE_CUDA_ARCHITECTURES=89-real``, ``CMAKE_BUILD_TYPE=Release``,
``GMX_SIMD=Auto``, ``GMX_FFT_LIBRARY=FFTPACK``, ``GMX_BUILD_UNITTESTS=ON`` and
``REGRESSIONTEST_DOWNLOAD=ON``. Build ``all tests`` and run CTest with
``CUDA_VISIBLE_DEVICES=0`` and no inherited ``OMP_NUM_THREADS`` override;
first select ``-L QuickGpuTest --parallel 1``, then the full suite serially.
The canonical systems and physical test definitions remain in
``tests/physicalvalidation/`` and ``tests/corpus/``. Record seeds in generated
working MDPs, retain resolved MDP/topology/TPR and outputs, and preserve the
original scientific thresholds.

Bromax development destinations are the `Actions page
<https://github.com/fabiobove-dr/bromax/actions>`_ and fork PRs. ``ci.yml``
coordinates quality/Linux/platform checks. The canonical CPU corpus landed in
`PR #41 <https://github.com/fabiobove-dr/bromax/pull/41>`_; paired manual/weekly
CPU benchmarking landed in `PR #42 <https://github.com/fabiobove-dr/bromax/pull/42>`_.
The `real paired run <https://github.com/fabiobove-dr/bromax/actions/runs/38234369133>`_
completed five argon pairs with both correctness gates passed and timing
indistinguishable from noise. Physical-validation CI remains tracked in
`#22 <https://github.com/fabiobove-dr/bromax/issues/22>`_. Local scientific
results do not establish that this CI workflow has been implemented.

Evidence required for a performance PR
--------------------------------------

A ``perf:`` PR identifies the unchanged physical/numerical invariants, required
equivalence tier, affected backend/precision/MPI/features, tests and tolerances,
reproducibility/restart behavior and conservative fallback. It supplies repeated
before/after end-to-end measurements with noise treatment and calibration cost.
Keep the old selection when a claimed winner is not distinguishable from noise.
Missing hardware or scientific evidence is an unmet merge gate, not a passing
result. Follow the repository ``AGENTS.md``, PR template and
`roadmap #33 <https://github.com/fabiobove-dr/bromax/issues/33>`_.

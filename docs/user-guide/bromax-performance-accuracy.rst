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
`#30 <https://github.com/fabiobove-dr/bromax/issues/30>`_ tracks continuous Bromax
reproducibility coverage; it is not assumed complete by this guide.

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
     - Local application/test build: 107/107 CTest entries passed; Linux Clang
       Release/Debug and GCC Release thread-MPI/serial passed in `PR #35 <https://github.com/fabiobove-dr/bromax/pull/35>`_.
     - Portable SIMD=None build; tests use the current source tree and supplemental
       2026.4 fixtures. This does not validate every SIMD ISA or statistical observable.
   * - CPU external MPI, double precision
     - GitHub configurations are being introduced by PR #35.
     - Results pending at this snapshot; no new validation claim. Hosted local
       MPI tests do not establish cross-node scaling/correctness.
   * - CUDA
     - Inherited implementation; no Bromax GPU validation result recorded here.
     - Unverified for fork changes. Local toolkit 12.0 is below this tree's
       minimum 12.1; do not bypass the build requirement to claim a pass.
   * - SYCL / HIP
     - Inherited implementations; no Bromax hardware results recorded here.
     - Unverified for fork changes; CPU passes provide no backend evidence.
   * - OpenCL
     - Inherited macOS build/test coverage retained in PR #35.
     - Run pending at this snapshot. A hosted device/driver test does not validate
       other vendors or imply CUDA/SYCL/HIP feature parity.
   * - DD / GPU PME decomposition
     - CPU built-in tests exercise supported multi-rank paths. GPU PME decomposition
       is opt-in and explicitly lacks substantial testing in inherited docs.
     - No Bromax multi-GPU or cross-node GPU validation recorded here.

Current development destinations are `Bromax Actions
<https://github.com/fabiobove-dr/bromax/actions>`_ and `PR #35
<https://github.com/fabiobove-dr/bromax/pull/35>`_ for CI migration. The existing
``build_cmake.yml`` represents Windows/macOS; proposed ``linux.yml`` adds CPU
configuration coverage. Dedicated performance/physical-validation workflows
are tracked by `#9 <https://github.com/fabiobove-dr/bromax/issues/9>`_ and
`#22 <https://github.com/fabiobove-dr/bromax/issues/22>`_; the versioned canonical
corpus is `#32 <https://github.com/fabiobove-dr/bromax/issues/32>`_. Until those
land, do not represent them as available workflows or validated baselines.

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

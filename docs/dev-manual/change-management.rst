=================
Change Management
=================

Bromax is developed independently at https://github.com/fabiobove-dr/bromax.
The upstream GROMACS repository is a read/fetch source, not a destination for
Bromax branches or pull requests.

Getting started
===============

Clone the fork and branch from its updated main::

    git clone git@github.com:fabiobove-dr/bromax.git
    cd bromax
    git fetch origin main
    git switch -c fix/descriptive-name origin/main

Check for unrelated work before switching branches. Report bugs and proposals
in the fork's `issues <https://github.com/fabiobove-dr/bromax/issues>`_; include
reproducible inputs, commands, versions and expected behavior as described in
:doc:`reportstyle`. Link the issue in a focused PR. Never send Bromax work to
``gromacs/gromacs``.

.. _code review:

Code review and validation
==========================

Use ``perf:``, ``fix:``, ``build:``, ``ci:``, ``refactor:``, ``docs:``, ``test:``
or ``chore:`` titles. Describe the resulting behavior and evidence using the
repository PR template. Follow :doc:`code-formatting`, :doc:`testutils` and
:doc:`../user-guide/bromax-performance-accuracy` for the affected code.

Open the PR with an explicit destination::

    gh pr create --repo fabiobove-dr/bromax --base main --head fix/descriptive-name

:doc:`github-actions` describes checks and diagnostic artifacts. Missing or
cancelled relevant checks are not passes. Reviewers should assess numerical
invariants, backend/precision/MPI compatibility and fallback behavior, not just
whether the build succeeds. Report unavailable hardware as an unmet gate where
that hardware is required. Fetch/rebase an unmerged branch and repeat affected
checks after resolving conflicts.

Squash-merge a validated PR into Bromax main, then delete its branch. Do not
rewrite published main history. Root ``AGENTS.md`` defines global development
rules; ``docs/dev-manual/bromax-upstream.md`` defines source baseline, import
provenance and conflict-sensitive validation for upstream synchronization.

.. _status label guidelines:

Issue labels
============

Use the fork's existing labels when helpful; issue/PR state and linked evidence
are authoritative. Do not assume the upstream label namespace or review roles
exist in Bromax. Keep discussion and actionable work on the linked GitHub issue.

.. _merge request status:

Pull request status
===================

Draft PRs are work in progress; open PRs await review/validation. A PR can be
closed without merging when superseded or rejected, with a reason and link to
its replacement where applicable. Merged PRs preserve their discussion and
validation evidence. Closing an issue requires satisfying its actual criteria,
not merely attaching a PR.

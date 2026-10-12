---
name: cpp
description: Change Bromax C++ or CMake code using existing formatting, targets, feature guards and regression tests.
---

Read root `AGENTS.md` and surrounding callers, tests and CMake targets.

- Use the existing utility/type and layer boundaries. Preserve error handling,
  validation, buffer ownership and event lifetimes when simplifying code.
- Trace compiled and linked sources for each affected build mode; distinguish
  core threading primitives from MPI emulation before removing thread-MPI code.
- Follow `docs/dev-manual/code-formatting.rst` for Clang 18 format/tidy commands
  and `.gitattributes` for file selection. Do not autoformat unrelated files.
- Reuse `src/testutils/` and the affected module's GoogleTest/CMake patterns.
  Cover the behavior that regressed, not just the new implementation shape.
- Configure and test affected precision/backend/MPI variants. Explain hardware
  gaps and performance-sensitive changes in the PR; source-level reasoning is
  insufficient evidence of GPU races or numerical equivalence.

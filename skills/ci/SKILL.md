---
name: ci
description: Change Bromax GitHub Actions coverage, build/test commands, caches and diagnostic artifacts.
---

Read root `AGENTS.md`, `.github/workflows/` and the scripts called by the workflow.

- Preserve explicit fork-only execution, read-only permissions and checkout
  without retained credentials. Do not use `pull_request_target` to execute
  untrusted PR code or send it to self-hosted hardware.
- Keep feature-branch runs on PR events and main runs on push; use concurrency
  keyed by workflow and PR/ref to cancel superseded work.
- Match checks to changed paths without leaving required-check names permanently
  pending on documentation PRs. Keep cheap gates before broad matrices.
- Separate compiler caches by configuration. Retain configure/build/CTest logs
  and JUnit results on failure; shell pipelines must preserve command failures.
- Use existing CMake targets and test fixtures. Version and checksum downloaded
  scientific inputs; normal CI must not require GitLab runners/tokens/projects.
- Validate YAML with `actionlint`, execute changed scripts, and inspect GitHub
  runs on the PR. A parsed workflow does not prove its matrix builds or tests.
  Declare GPU and scientific-validation gaps explicitly.

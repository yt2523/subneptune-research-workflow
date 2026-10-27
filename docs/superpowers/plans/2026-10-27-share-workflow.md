# Portable research-workflow release implementation plan

> For agentic workers: use the approved role separation: Codex specifies and reviews; DeepSeek implements. Preserve historical outputs byte for byte.

Goal: a public, cloneable research project with portable bounded coding/test/review workflow, external credentials, offline demo and explicit research gates.
Architecture: retain MAGRATHEA at repository root and immutable experiment archives. Reuse Store state/hash gates; add a Python-standard-library portable runner. A checked-in ordered dependency/priority plan provides durable milestones; no autonomous change of scientific assumptions.
Tech stack: Python >=3.10, Git; optional Codex CLI and DeepSeek HTTPS API. Solver requires separate Linux/WSL compiler + GSL build. No Cline installation required for shared runtime.
Spec: docs/workflow/ACCEPTANCE.md. User authorized publication and implementation on 2026-10-27.

Constraints: no new scientific runs, no key publication, no local credential values in prompts/logs, no modification of original checkouts, one writer, code/test execution is not an OS sandbox. Retain third-party MIT attribution.

- [x] Copy existing engineering branch and workflow source (exclude private logs/runs).
- [x] Write acceptance tests first; observe failure for missing portable interface.
- [x] DeepSeek implements portable config/credential handling, bounded milestone runner, test execution and independent review adapters.
- [x] Verify offline multi-node run, resume, rejection/repair, budgets, stale evidence and invalid input.
- [x] Document roles, short rules, TP acceptance, keys/setup, scientific limits, provenance and reproducibility.
- [x] Independent clean-context review; DeepSeek fixes actionable issues.
- [x] Secret/publication scan and clean-clone checks.
- [x] Public GitHub creation/push, verify remote SHA and visibility.

Review focus: credentials outside repo and never logged; path/symlink escapes; test commands fixed before coding and evidence tied to exact files; no scientific completion claims from fixture tests; interrupted/failed tasks must not become passed; tests/reviewer unavailable means stop with durable next step.

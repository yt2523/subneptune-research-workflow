# Architecture

```text
repository/
  src/ + tabulated/ + Makefile       MAGRATHEA scientific engineering
  experiments/subneptune-20261027/  immutable results + original tool snapshot
  workflow/portable.py              portable standard-library coding/test/review loop
  workflow/examples/                no-key demo and local configuration starting points
  workflow/tests/                   infrastructure acceptance and regression tests
  workflow/legacy/                  original Windows/Cline workflow source, historical
  docs/                             current research state, contracts and operating rules
  .runs/                            local staged source, state and evidence (ignored)
```

Human/Codex supplies a plan with explicit acceptance, dependencies, priorities, writable scope and immutable test commands. Deterministic selection chooses the highest-priority ready task. DeepSeek receives bounded current files and latest failure; controller applies validated proposals only in a staged copy and executes fixed tests. Independent Codex CLI/API reviewer judges the tested snapshot. After pass, state advances; after rejection, DeepSeek repairs. Protocol/transport failures pause; five ineffective valid repairs request diagnosis. Budgets bound live calls and wall time.

This is a declared-plan executor, not a free-ranging research planner. Codex updates priorities when scientific evidence changes; the runner never invents physical assumptions. Source staging copies only declared files/context; a C++ build needs all its declared dependencies. It does not silently clone the entire machine.

Credential boundary: caller supplies external file; runtime reads known keys only, does not store file contents in state or prompts. Codex CLI authentication remains managed by Codex. Raw private provider transcripts from original research are not imported. Tests execute code with the user's privileges: staging + allowlist is not an OS sandbox. For untrusted code, use a container/VM or appropriately restricted host.

Partial state and recovery are observable through status. Completion, budget exhaustion, transport failure and scientific authorization are distinct. Optional skills guide human/agent operation; they are not runtime Python dependencies.

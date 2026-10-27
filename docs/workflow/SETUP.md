# Setup and external credentials

## Prerequisites

Python >=3.10 for portable workflow and tests. Git for obtaining/versioning the project. For live coding: working DeepSeek API access. For independent review: either installed/authenticated Codex CLI on PATH, or a separately configured compatible reviewer API with OPENAI_API_KEY. No new provider login or installation is automated.

Python 3.12 on Windows is the local validation environment for this release; read RELEASE_VERIFICATION.md for actual cross-platform test status. Scientific solver separately needs Linux/WSL, g++, make and GSL. Python plotting uses numpy/scipy/matplotlib only when doing those tasks, not the offline workflow demo.

## First run

Start with README offline commands. Review workflow/examples/demo.json. It uses isolated .runs storage and actual deterministic tests; fixture model verdicts are clearly labeled. Do not reuse its run_dir for a different contract or switch it to live: give a live config a fresh run_dir.

Copy `workflow.local.example.json` at the repository root to `workflow.local.json`. This one-task live smoke test is deliberately separate from offline fixtures. `project_root`, `run_dir` and other configuration paths resolve relative to that JSON file. Keep the config in the repository root to use project_root `.` and run_dir `.runs/my-first-live`. `context` lists immutable input/support files; tasks' `scope` lists writable implementation files only. Include test scripts as context, never writable scope. All files needed to execute tests must exist in the staged source copy.

Default coder config: `{ "model": "deepseek-v4-pro", "base_url": "https://api.deepseek.com" }`.
Default reviewer config: `{ "provider": "codex" }` (no pinned model; user's CLI default). For API review use `{ "provider": "api", "base_url": "https://api.openai.com/v1", "model": "YOUR_AVAILABLE_REVIEW_MODEL" }` and external OPENAI_API_KEY. Do not guess another user's model access or substitute providers silently.

## Secret file

External UTF-8 JSON:

```json
{"DEEPSEEK_API_KEY":"your-key","OPENAI_API_KEY":"only-if-using-api-review"}
```

Or external dotenv file:

```dotenv
DEEPSEEK_API_KEY=your-key
# OPENAI_API_KEY=only-if-using-api-review
```

`--credentials` points at the file. Do not paste it in TASK.md, config, issue, screenshot or chat. Keep it outside the repository; the runner rejects files inside the repo. Existing arbitrary provider config files are not parsed: make this small JSON/dotenv file locally, or adapt the loader after review. Endpoint host receives that provider's key; use only trusted official/configured endpoints.

## Live run

```sh
python -B workflow/portable.py doctor --config workflow.local.json
python -B workflow/portable.py run --config workflow.local.json --credentials /path/to/keys.json --allow-tests
python -B workflow/portable.py status --config workflow.local.json
```

Review command argv before allowing tests. Controller executes declared checks on behalf of builder; it does not give model arbitrary terminal access. No shell is used. API calls and tests have deadlines. Errors/quotas pause rather than blindly retry. max_model_calls is a hard cap on logical adapter invocations: one direct API request or one Codex CLI review launch. Codex CLI can make multiple underlying requests; those hidden/internal requests are not individually capped by this counter. Per-launch wall timeout is enforced. Reported provider token usage is accounting evidence, not an invoice or a strict monetary/token cap; unavailable CLI usage must stay unknown.

A successful result is still in run_dir/source. Compare it with original files; independent review must match the tested snapshot before integrating. Do not copy an entire staged directory over an active checkout. Only move approved scoped changes and commit. To start a changed plan/changed source, choose a fresh run_dir; stale evidence must not certify changes.


## Deliberate limits

The current model proposal protocol writes complete UTF-8 text files within declared scope (up to 10 files per proposal); deletion, rename, binary assets and arbitrary terminal tools are not supported. Keep scope small; max_context_chars pauses an oversized prompt instead of silently sending an entire repository. Declared context/test dependencies must be staged explicitly. The runner executes the dependency/priority plan supplied by human/Codex; scientific reprioritization is a coordinator decision, not an autonomous hidden research expansion.

The logical call count persists across resume; the wall-time deadline applies to each invocation. A subprocess timeout is not a full HPC/child-process-tree cancellation system. Use reviewed local checks; long solver jobs, distributed work and untrusted code require their own execution environment and authorization. Automatic integration/push of generated code is intentionally a coordinator step after independent acceptance, not an action a builder can request through the proposal protocol.

Task dependencies do not automatically infer complete regression coverage: later milestones should include earlier critical invariant checks in their fixed tests. Keep those checks deterministic rather than asking a model to reinterpret pass/fail each time.

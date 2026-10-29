# Research workflow operating contract

Coordinator: read this file, docs/PROJECT_STATUS.md and docs/workflow/SHORT_RULES.md; then only the task-relevant acceptance document. Bounded builders/reviewers: use the supplied task contract and relevant acceptance criteria; do not load project history unless it is needed for that task. Keep chat concise. User directions override defaults. Do not load every skill or every historical report.

## Roles

- Human: owns research aims, material physical choices, budget and publication scope.
- Codex coordinator: specifies tasks/acceptance, decides priorities from scientific uncertainty and dependencies, diagnoses failures from the first failed round, records decisions and archives milestones. Normally does not write implementation code.
- DeepSeek builder: primary implementation and repair. May request/trigger only the predeclared test commands through the controller. Cannot edit acceptance criteria, test definitions, credentials, or plan. A model claiming PASS is not test evidence.
- Independent Codex/GPT reviewer: fresh context, read-only, evaluates acceptance coverage, unit/physics assumptions and actual test evidence. Findings are passed / failed / insufficient evidence. The implementing instance cannot give final independent approval.
- Deterministic controller: executes predeclared checks, records exit codes, hashes, usage and state. This is software, not an extra paid agent. Test execution on DeepSeek's behalf does not change who owns independent acceptance.

Same root cause with five valid ineffective DeepSeek repair rounds: Codex may directly make a narrowly scoped repair after diagnosis. Timeouts, quota and JSON transport errors do not count as valid repairs. Broad rewrites go back to DeepSeek. Any Codex implementation change requires a fresh uninvolved reviewer. The portable runner stops at needs_codex_diagnosis; it does not silently switch coder models.

## Skills (optional mechanisms; never prerequisites for cloning)

Coordinator: brainstorming / writing-plans for new substantial work; systematic-debugging for failures. Builder: minimal-change principles from ponytail, test-driven-development for behavior changes. Reviewer: requesting-code-review / scientific-critical-thinking as applicable. Anyone claiming completion: verification-before-completion. Literature only: LR-assistant when configured.

Subagent-driven-development and dispatching-parallel-agents are available in the author's environment; use focused independent agents only when they add evidence. Do not spawn an agent per numerical case. A skill name does not make DeepSeek load its contents: transmit the bounded task contract explicitly. No mandatory plugin installation or private skill path dependency.

## Scope and continuity

Main research question: under the same outer boundary and density EOS/composition treatment, how does TP shape change inferred gas mass? Restricted mode0 prescribed-TP v1 is implemented. The frozen numerical contract stopped overall FAILED after8/20 fits (individual cases passed; no recovered composition); see experiments/prescribed-tp-20261028/README.md. Do not restart that failed contract or spend unused cases automatically. Fixed high-pressure EOS choice and any new implementation/provider budget require the operator’s decision; the author’s44-call DeepSeek allowance is exhausted. A single human-approved Codex cleanup-order repair is not broad permission to take over implementation. Do not repeat completed grids to prove workflow infrastructure.

Portable runner uses staged source copies. Only approved changes are transferred back after review. One writer per run. Continue approved dependent tasks without asking between each small step; stop for missing scientific decisions, budget, permission boundary, or externally blocked state. Preserve explicit next action and stop reason. Never invent a successful reviewer verdict.

## Versioning

Milestone archive: inputs + source/config identities + outputs/checks + limitations + next step; commit scoped changes and push the authorized repository/branch, verify remote SHA. Keep older output bytes unchanged; new results get new directories. No force-push, secret files, private papers, or unreviewed provider transcripts. Existing Magrathea archive branch remains untouched; this shareable repository is its continuation for portable workflow work.


## Reporting problems

Use GitHub Issues in this repository. Prepare a minimal reproduction with commit/OS/Python, command, expected/actual behavior, stop_reason and redacted evidence. Use .github/ISSUE_TEMPLATE/bug_report.md. Draft first; submit only with the operator's authorization. Never attach keys, API files, raw private sessions or whole research datasets. Do not auto-open repetitive reports or run new experiments merely to report an infrastructure bug.

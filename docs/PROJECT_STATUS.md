# Current project state / 当前状态

As of2026-10-29. Synthetic engineering cases; no selected observed-planet posterior.

- Restricted mode0 prescribed-TP v1 is implemented and independently reviewed. It uses fixed Gas(mu2,n2), zero temperature jumps and actual Mfit strictly below gas. This EOS is an engineering fixture, not an approved target-planet atmosphere.
- New numerical run: eight individual full fits passed their frozen checks; overall composition-recovery contract FAILED because the two endpoint radii did not bracket the B target. Used8/20, bisection0, no inferred composition. No automatic continuation with the unused12 calls.
- Same-boundary/EOS A30/B40 comparison: B radius +2.117466% relative toA; targeted tighter/refined changes are much smaller. These are consistency checks, not a global error bound or physical inference.
- A samples are nonmonotonic across0.2%,1%,8% gas. High-fraction ideal-gas base density exceeds adjacent solid. This flags applicability; it does not independently prove a code defect, instability, no interior root or uniqueness.

Read [the report and figures](../experiments/prescribed-tp-20261028/README.md), then [the next EOS decision/acceptance gate](../experiments/prescribed-tp-20261028/NEXT_STEP.md). The archive contains original inputs/outputs, identities and byte hashes; verify_archive.py does not run models. Original numerical source3608c3d; unchanged baseline9e74aac is in repository history. [Implementation ledger](TP_IMPLEMENTATION_PROGRESS.md), [acceptance status](TP_ACCEPTANCE.md).

Next minimum: confirm the real H/He density-EOS source/composition and explicit coverage/failure policy before a new implementation or numerical contract. Read-only table inventory is done; no real-EOS model was run. The existing HHe_tabulated hybrid100bar selector and table-edge fallback are not automatically accepted for this interface. Do not move gas_default's100bar boundary as a pure thermal experiment; it also changes molar mass3→2.

Current-session limits: DeepSeek44/44 calls exhausted. Human authorized Codex only one local stale-sidecar cleanup ordering repair, which passed independent review and7 pre-solver CLI cases. No broad Codex physics implementation permission. Cloning/doctor/offline workflow does not authorize science runs; a new operator uses their own explicit scope/budget/run directory. The portable API workflow itself is not claimed to have orchestrated this research execution.

Historical54 semi-grey/8 mode0/67 boundary-temperature-recovery cases remain archived and were not repeated. Preserve original dirty research checkouts and older bytes; new outputs stay onD:. No install/authentication was repeated. For generic workflow infrastructure see docs/workflow/RELEASE_VERIFICATION.md.

New explicit user direction continues Stage4 under a separate [reciprocal follow-up plan](superpowers/plans/2026-10-29-stage4-reciprocal.md): same curves/EOS/1% truth, direction A→B, post-failure selection disclosed. No C++/EOS changes or paidAPI extension; at most12new fits and20cumulative. Original failed run remains closed. Contract is independently reviewed and frozen before first new fit; success is not yet claimed.

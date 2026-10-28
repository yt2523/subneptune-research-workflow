# TP implementation ledger

Plan: superpowers/plans/2026-10-28-prescribed-tp.md. Starting revision 4d412570fe2af972ec752796519fedb0c708d65e.

2026-10-28 human direction: continue through stages without stopping between ordinary milestones. This supersedes Stage1-only authorization/confirmation text in the earlier plan. Material target-planet assumptions remain separate; the fixed mu=2 model is a synthetic verification fixture.

## Task1: profile and configuration infrastructure complete

DeepSeek implemented immutable CSV/log-pressure interpolation, optional cfg validation and main input guards. Codex supplied fixed independent tests and diagnosed failures; no Codex scientific implementation patch. Fresh uninvolved reviewer rejected earlier defects; after repairs granted scoped Task1 code approval. This does not approve solver integration or scientific results.

Actual checks: 38 profile assertions,28 settings assertions,12 CLI validation cases rejected before any integration, clean-directory narrow build exit0, full solver link exit0. One CLI oracle expected the word requires while the correct message said required; corrected wording against the already recorded exit1/log, solver behavior unchanged. Evidence: tp-task1-verification.json.

The first existing Cline invocation was explicitly in act mode (saved mode=act; no --plan flag); it produced prolonged planning before stubs, then was stopped. Do not claim this was proven to be plan-mode misconfiguration. Same DeepSeek model subsequently used official direct API with thinking disabled and bounded text edits. No installation/authentication change. Truncated or mismatched proposals were rejected or recovered only as complete uniquely matching file/edit entries, with original responses retained privately on D:. Portable workflow runtime was not modified and is not claimed to have orchestrated this run.

Task1 checkpoint: full TP interface was not implemented; its enabled-input guard deliberately prevented solving. No full planet invocations or historical grids were run for Task1. See current Task2 state below.

Archiving: scoped Task1 files committed on the existing main continuation; remote SHA recorded in the executing chat after push. Existing dirty research checkouts and historical archived output bytes preserved. Existing line endings were mechanically retained where possible; this is not a solver algorithm change.

## Task2: context, common effective state and fitting guards complete

DeepSeek implemented fixed-mu2 gas selection, explicit per-solve context, density/temperature agreement, knot-aware stepping, gas-base continuity and strict non-gas fitting guards. Codex supplied fixed tests and diagnosis. Independent review rejected earlier versions and approved repaired R4 actual source; model prose was not accepted as evidence.

Actual checks: 18 RHS assertions,353 knot assertions,118 constructor assertions; reverse traversal and near-knot entry at zero/nonzero mass coordinate; early0.9995-Mfit truncation rejection; original coverage error preserved and latched across later callbacks. Two legacy OFF correction fixtures produce byte-identical outputs to unchanged baseline (615 and599 rows). These controlled constructor/callback integrations are not full converged planet fitting or historical batch repeats. Evidence: tp-task2-verification.json and evidence/tp-task2-checks.log.

Current full TP interface: PARTIAL. Valid enabled CLI input still stops with TP diagnostics not implemented. Task3 high-precision sidecar and CLI activation remain pending; no full planet invocations or synthetic inference claims. The density EOS mu2 remains an engineering fixture; deeper temperature coupling is retained. Existing Cline run was act mode; plan mode was not the observed cause of delay.

Provider control: human explicitly approved maximum12 additional bounded DeepSeek calls, raising direct-call cap32 to44. Actual usage retained privately; no API credentials are included in this repository. The frozen new whole-planet budget remains20 including failures, used0 at Task2 archive.

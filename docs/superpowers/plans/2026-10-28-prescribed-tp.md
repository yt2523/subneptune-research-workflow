# Prescribed gas TP Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to follow these checkboxes through the existing DeepSeek builder/controller workflow. Optional skills are not installation prerequisites. Implementation is a later stage; current authorization covers the read-only audit and these documents only.

**Goal:** Add an optional gas T(P) interface whose density and thermal paths agree, without changing legacy default behavior.

**Architecture:** A standard-library immutable TP evaluator plus explicit per-solve context; existing gas-density EOS reused through a fixed selector. Keep three-state integration and non-gas matching, reject unsupported matching/coverage cases explicitly.

**Tech Stack:** Existing C++11/GSL solver; stdlib-only C++ evaluator tests; existing Python controller for evidence/fixtures, no new provider or dependency installation.

**Spec:** [TP_INTERFACE_SPEC.md](../../TP_INTERFACE_SPEC.md); [TP_SOURCE_AUDIT.md](../../TP_SOURCE_AUDIT.md); [TP_ACCEPTANCE.md](../../TP_ACCEPTANCE.md).

## Global Constraints

- Mode0 only, optional OFF by default. No EOS-table/global Gas edits, no moving the 100-bar boundary.
- gas_fixed_mu2 is a software-validation fixture, not an approved target-planet atmosphere.
- Three temperature jumps zero; nonzero gas and non-gas masses; adjusted Mfit strictly below gas; no corrected/truncated fits accepted.
- T–lnP interpolation; CSV P_bar,T_K; no extrapolation/clamp; fail on missing coverage.
- No new scientific/model runs, API calls, installations or authentication under Stage 1. Numeric integration checks need a separate frozen run contract and authorization.
- DeepSeek implements and runs permitted checks; Codex owns acceptance and diagnosis. Same-root five valid ineffective repairs permits narrow Codex repair, followed by uninvolved review.
- Work in the shared D: repository on the continuing authorized branch; preserve original dirty checkout and historical outputs. Stage/commit explicit files only.

## Review Focus

1. Wrong-type/missing options, whitespace paths, duplicate/nonfinite/overflow CSV values: fail explicitly (Task 1).
2. Boundary drift/coverage failures during rejected ODE trial steps: no silent clamp or stale success (Task 2).
3. Layer entry/skip direction and density evaluated with stale temperature/pressure: same effective state, non-gas untouched (Task 2).
4. Knot derivative jumps and gas-located fitting point: controlled stepping or explicit rejection, full-rank matching retained (Task 2).
5. Eight-digit output hides residuals; code exit0 masquerades as convergence: high-precision actual diagnostics, numerical gates remain pending (Task 3).

## Task 1 — TP evaluator and configuration validation

**Files:** create src/tp_profile.h, src/tp_profile.cpp, tests/test_tp_profile.cpp, tests/test_tp_settings.cpp; modify src/parser.h/.cpp, src/main.cpp and Makefile (test targets only). No hydro edits in this task.

**Consumes:** cfg directory plus optional tp_profile_file and existing mode/mass/jump options.
**Produces:** TPProfile::load_csv, at_cgs, min_pressure_cgs, max_pressure_cgs and TPState exactly as specified; Settings::HasOption(const std::string&) const. Enabled valid configuration may be parsed, but must fail with TP integration not implemented until Task 2 lands; never fall through to the old solver while claiming TP is active.

- [ ] Codex supplies fixed tests/assertions; DeepSeek may add cases but cannot weaken acceptance tests.
- [ ] Test exact nodes and analytic linear-in-lnP fixture: CSV nodes (1 bar,300 K), (100 bar,500 K); at 10 bar expect 400 K; derivative expect (200/ln100)/1e7 K/cgs; both at <=1e-12*max(1,abs(expected)). Test first/last/internal knot derivative convention.
- [ ] Test nonmonotone positive T accepted; duplicate/descending P, NaN, Inf, zero, negative, overflow on conversion, trailing junk, extra column, bad header/BOM, missing/unreadable file and insufficient rows rejected.
- [ ] Test missing option OFF, malformed/empty present option errors, whitespace path rejected before parser strips it, cfg-relative resolution independent of working directory, unsupported mode/selector/masses/jumps rejected. Missing OFF option must not read a TP file.
- [ ] Run each future test target before implementation, record intended assertion failures; compiler/tool absence is not a valid red result.
- [ ] DeepSeek implements minimum evaluator/config changes; error messages include path/row or option.
- [ ] Future declared checks: `make test-tp-profile` and `make test-tp-settings`. Each builds its dedicated executable under tests/.build/ and executes it; all assertions must pass. Add tests/.build/ to ignore before first compilation; existing build environment only. No planet invocation.
- [ ] Codex reviews diff and controller evidence, commits explicit Task 1 files after approval. New provider/build executions need their own stage authorization; do not launch this task from the Stage 1 plan automatically.

## Task 2 — Mode0 context, effective state and boundary wiring

**Files:** modify src/hydro.h/.cpp, src/main.cpp, src/phase.h/.cpp; create tests/test_tp_hydro.cpp; update Makefile narrow target. No EOS.cpp/EOSlist.cpp or tabulated/ changes without a separately reviewed necessity.

**Consumes:** const TPProfile* from Task 1; existing Gas EOS and component masses. **Produces:** defaulted final `const TPProfile* tp=nullptr` argument on fitting_method, Rloop and the two mode0 hydro constructors; const pointer and enabled/error context in loop_params/mass_params. Legacy callers compile unchanged. Implementer chooses private context struct names; record them in delivery.

- [ ] Pin tests for active/inactive gas slot selection in both directions, including zero-mass water/mantle slots and a finite non-gas core; never infer gas solely from pressure/EOS name.
- [ ] Pin callback tests evaluating density at the same effective T as the RHS at trial states, accepted endpoints, gas base and outer boundary; deliberately perturb stored y[2] and ensure density uses prescribed T. Record pre-projection discrepancy separately.
- [ ] Pin RHS sign/chain rule in each direction and forbidden adiabatic callback use; require finite derivative failures to propagate through GSL without exceptions crossing its boundary.
- [ ] Pin no-coverage/outer-anchor mismatch, knot stepping/reset, invalid adjusted Mfit, gas-only/zero-gas input, and corrected-fit rejection. Test actual post-adjustment Mfit, not only 0.2 Mtot.
- [ ] Implement fixed selector and explicitly propagate context through R_hydro, Rloop, constructors, fitting_error and every params reset/aggregate initializer.
- [ ] Apply effective state before every enabled gas phase/density call and accepted-state write. Keep original path untouched when nullptr. Integrate non-gas thermal state with continuous zero-jump gas-base boundary.
- [ ] Future declared check: `make test-tp-hydro` (dedicated harness, no historical grid). Any harness that executes full planet integration must wait for the numerical run contract below; source wiring assertions alone do not pass TP04/07/09.
- [ ] Codex and uninvolved reviewer audit every state path; unresolved wiring is a blocker. Commit only reviewed files.

## Task 3 — Diagnostics and numeric-check handoff

**Files:** create tests/check_tp_model.py, docs/TP_NUMERICAL_RUN_CONTRACT.md and tests/fixtures/tp_run_contract.json; modify src/hydro.h/.cpp and src/main.cpp for actual diagnostics, plus tests/test_tp_hydro.cpp.

**Consumes:** exact build/config/profile identities and solver evidence from Task 2. **Produces:** <output_file>.tp.json schema from specification; Python checker takes `--diagnostics PATH --contract PATH`, exits0 only if all declared checks pass. docs/TP_NUMERICAL_RUN_CONTRACT.md explains the choices; tests/fixtures/tp_run_contract.json holds the actual machine-readable values. Do not create a runnable numeric contract with invented tolerances.

- [ ] Pin sidecar schema, max_digits10 output, nonfinite residual rejection, failed-run nonzero status, stale sidecar prevention and no default-mode extra outputs. Store raw Ri,Ro,Pi,Po,Ti,To plus normalized residuals before branch erasure.
- [ ] Pin checker failures for hash mismatch, missing coverage, failed ODE/fit status, fitting correction, effective T/density discrepancy above contract thresholds, and missing numeric thresholds. Test valid fixture acceptance and deliberately invalid fixtures without running planets.
- [ ] Record exact build/compiler/GSL/source/config/profile versions; freeze radius/mass/fit residual thresholds, interpolation refinement and tighter ODE comparisons BEFORE new model runs. Codex sets justified values from output precision and applicable stability evidence; builder cannot lower them.
- [ ] Prepare the smallest authorized numeric check list: unchanged OFF baseline, analytic TP checks, fixed-EOS forward pair, resolution/tolerance check. Declare number/time cap and stop rules; no old 54/8/67 grids, composition search or target-planet claim.
- [ ] Stop before numeric execution until authorized. After actual evidence passes TP01–09 as applicable, independently review and archive; only then propose synthetic recovery (TP10) as the next scientific milestone.

## Stage 1 closure

- [x] Existing report/acceptance and relevant source paths read.
- [x] Shared/original Git states checked read-only; original changes preserved.
- [x] Scope, effective-state contract, fixed-EOS fixture and fitting restriction written.
- [x] Fresh bounded builder-readability review; no important unresolved implementation question reported. Review applies to design readability only, not scientific/code acceptance.
- [x] Verify document links, source identity and documentation-only diff; record exact evidence in docs/tp-stage1-verification.json.

Archive procedure: commit scoped docs, push the authorized continuation branch if network access is available, and report verified remote SHA in the handoff. Archive identity belongs to Git and the final handoff, not a self-referential commit hash embedded in this document.

Next authorized action after this milestone: present Stage 1 result. No automatic Task 1 execution.

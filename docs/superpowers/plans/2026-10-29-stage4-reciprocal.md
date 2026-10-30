# Stage4 reciprocal recovery verification plan

> For agentic workers: use executing-plans for this deterministic verification task and a focused independent reviewer. No solver implementation or provider calls are authorized by this plan.

**Goal:** Establish one independently validated local synthetic recovery and signed gas-mass bias using the unchanged A30/B40 pair and1% truth, while preserving the failed opposite direction.

**Architecture:** Reuse authenticated forward artifacts; a new verification-only Python driver calls the existing binary in fresh directories. Existing SciPyBrent in log fraction proposes samples; explicit evaluated sign bounds and separate checks own acceptance. No src/, Makefile, old checker, old8 cases or old contracts are edited.

**Tech stack:** Existing Python3/SciPy, current WSL/GSL binary; no install/auth/provider calls.

**Spec:** tests/fixtures/tp_reciprocal_contract.json (freeze after review before any new fits).

## Constraints and review focus

- New human instruction continues stage4; this is a separate post-failure-selected design, not automatic restart of the closed contract. Same physics, outer boundary and truth fraction. OriginalFAILED remains visible.
- At most10new search fits including lower endpoint,2 confirmations; cumulative old8+new<=20;120s/case. PaidAPI44/44 stays unchanged.
- Actual bracket signs and width plus radius tolerance determine convergence, not a library flag. Never forge[root,root]. Handle nonbracketing, nonfinite values, exhaustedbudget and failed model by stopping.
- Every accepted model passes unchanged highprecision fit/T/density/mass/coverage/hash checks. Cached cases retain original source/controller identities. Everynewcase must pass recorded density branch screen, which is not physicalvalidation.
- Both tight-only and collinear-only confirmation cases use the exact inferredfraction. Report residuals, remaining signed interval, numerical change and conditional signed bias, not uniqueness/statisticalconfidence.

## Task1: verification helper and orchestration

Create tests/tp_recovery_search.py (pure bracket-search helper), tests/test_tp_recovery_search.py (analytic/error/budget tests) and tests/run_tp_reciprocal.py (new-case controller). Helper consumes a radius callback, authenticated endpoints, target and frozen tolerances; produces an actuallyevaluated candidate and signed enclosing endpoints. Controller consumes source/cache/newoutput paths and contract; produces before-run identities, count-before-launch ledger and original-format case artifacts checked by existing check_tp_model.verify.

- [x] Write/run meaningful failing analytic and fault tests before helper implementation.
- [x] Implement minimum wrapper using installed SciPy; no new physical solver.
- [x] Pass analytic root, nonbracket-with-interiorroots rejection, nofakecollapse, nonfinite, callbackfailure and budget tests.
- [x] Independent design/code review; freeze contract and archive before any new fullfits.

## Task2: bounded follow-up

- [ ] Verify original8-case state/hashes/currentbinary, cachedtargetA and upperB, controls and gas composition; freeze all actual scientific/controller/dependency identities.
- [ ] Compute newlowerB0.0005; require genuine target bracket with cachedB0.01.
- [ ] Search within budget; everyacceptedpoint retains provenance and branchscreen.
- [ ] Atactualcandidate run one tighter-only and one collinear-only check; both mustpass everyexistinggate and targetmatch.
- [ ] Fresh independent audit of rawoutputs, signs, massbias and claimlimits; archive samecontinuationbranch, keeping originalfailure intact.

If any criterion fails, record failure and diagnose from evidence; do not silently tune the contract. Completion is conditionalengineeringstage4 evidence, not realisticEOS/observedplanetinference. Stage5 remains separate.

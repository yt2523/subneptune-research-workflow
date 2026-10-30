# TP interface acceptance / TP 接口验收表

Current status: restricted v1 and one selected reciprocal local composition recovery pass their bounded checks; original direction remains FAILED. The requirement table below is unchanged. Implementation cannot lower it to make tests pass. Codex specifies; human confirms material physical choices; DeepSeek implements; uninvolved reviewer checks evidence.

Stage 1 design (2026-10-28): [interface contract](TP_INTERFACE_SPEC.md), [source audit](TP_SOURCE_AUDIT.md), [task plan](superpowers/plans/2026-10-28-prescribed-tp.md). This adds a concrete proposed scope without marking any scientific gate passed or relaxing the requirements below.

| ID | Requirement | Required evidence |
|---|---|---|
| TP01 | Default-off interface leaves existing behavior unchanged | Fixed baseline source/build/config identity and default-profile/radius regression; output precision and numerical tolerance declared before run |
| TP02 | Explicit P/T units; finite positive values; strict order; reject duplicates/malformed data | Unit tests for conversion, invalid inputs, ordering and repeat values |
| TP03 | Interpolation and out-of-range behavior fixed in specification | Analytic curves plus resolution study; default reject outside coverage; no silent extrapolation |
| TP04 | Density and both integration directions evaluate the same prescribed T(P) | Source-path audit plus independent analytic/controlled numerical case; actual T(P) residual across gas layer |
| TP05 | Do not simultaneously force original adiabatic temperature equation | Equation/path evidence; forward/backward fit consistency |
| TP06 | Same outer P/T, total mass and density EOS/molar-mass treatment across TP-shape pair | Machine-readable configuration comparison; gas_default phase/mu mixing explicitly excluded |
| TP07 | Preserve mass/pressure boundaries and fitting diagnostics | Actual boundary residuals, finite/monotone profiles; internal convergence state if available, otherwise explicit limitation |
| TP08 | Coverage reaches gas-layer base for every recovered fraction | Recorded maximum pressure and table bounds; a negative coverage test must fail clearly |
| TP09 | Numerical sensitivity smaller than claimed TP-shape signal | Declared resolution and tighter ODE/fit controls; report residuals rather than binary slogans |
| TP10 | Composition recovery follows validated forward comparison | Fixed synthetic truth, signed residual/bracket; no confidence-interval or observed-posterior claims |
| TP11 | Scientific interpretation matches approximation | Label prescribed curves as sensitivity cases, not self-consistent RCE; ideal gas/EOS validity and solid-layer temperature coupling recorded |
| TP12 | Reversible, auditable delivery | Baseline, optional interface, scoped commits, exact source/inputs/output hashes, independent review and rollback description |

Do not infer new numeric tolerances from old studies: set each threshold before its corresponding new experiment, using output precision and baseline stability. Historical 2e-5 radius matching was a past experiment's stopping rule, not a universal physical accuracy claim.

## Current evidence, without lowering the requirements

Original-source run3608c3d: [report and raw evidence](../experiments/prescribed-tp-20261028/README.md). Overall FAILED,8/20 full fits,0 bisection, no inferred composition.

| ID | Current bounded status |
|---|---|
| TP01 | Solver OFF PASS: full-precision radii equal, legacy profile bytes equal. Full CLI OFF was not separately executed; CLI failure handling/source paths reviewed. |
| TP02 | Parser/unit checks PASS (Task1/2 evidence). |
| TP03 | Analytic interpolation/out-of-range checks and collinear-node integration PASS. No arbitrary-curved-profile accuracy claim. |
| TP04–TP05 | v1 common gas T/density and chain-rule paths PASS; controlled tests both directions. Whole-planet fitting point remains in non-gas material. |
| TP06 | A/B same5ME,0.1bar,300K and fixed density EOS PASS. |
| TP07 | Tested cases have status0/no corrections, small raw fit residuals, matching masses/boundaries; rounded saved M/R/P profiles show no reversal. No physical-stability claim. |
| TP08 | Six tested TP cases and negative coverage fixture PASS. No recovered-fraction domain established. |
| TP09 | Targeted tightening/refinement PASS under frozen thresholds; not a rigorous global error bound. |
| TP10 | FAILED: fixed recovery endpoints do not bracket target; no inferred composition or uniqueness. |
| TP11 | Approximation labels/limitations recorded; real high-pressure EOS applicability remains unvalidated. |
| TP12 | Source/inputs/output identities, raw byte archive, independent review and scoped continuing commits preserved. |

Any new real-EOS implementation or recovery sampling needs explicit physical choices and a new authorized contract; the unused budget is not a waiver.

## Separate reciprocal follow-up: conditional Stage4 PASS

[Full evidence](../experiments/prescribed-tp-reciprocal-20261030/README.md). Original failure above is unchanged. Under the same curves/EOS/1%truth, the new A→B pairing recovered0.243603878% gas with signedbias−0.756396122percentagepoints. Actual sign bracket width5.6533e-6 and radiuserror2.0373e-8 passed both frozen stopping gates. Same-fraction tighter/refined checks passed all old model gates; refinedmodel actually used10nodes/5snaps. Everytestedbranch density screen passed without being treated as physicalvalidation.

TP10 is therefore PASS for this one hindsight-selected local engineering recovery, not for the failed original direction or general/global/observed inference. TP08/09 cover its evaluated points and confirmations, not all physicalEOS regimes. Sixnewfits/14cumulative,0newAPI; no C++changes or criteria relaxation. Stage5 remains separate.

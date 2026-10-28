# TP interface acceptance / TP 接口验收表

Status: NOT IMPLEMENTED; these are future scientific gates, not passed checks. Implementation cannot lower this table to make tests pass. Codex specifies; human confirms material physical choices; DeepSeek implements; uninvolved reviewer checks evidence.

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

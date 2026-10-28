# Prescribed-TP numerical acceptance contract

Status: frozen before first full planet invocation. Machine values: ../tests/fixtures/tp_run_contract.json. This is a synthetic software/sensitivity fixture, not a TOI-732 c atmospheric model or posterior.

Use 5 Earth masses, P0=0.1bar,T0=300K, existing fixed Gas mu2,n2, no water, core:mantle0.325:0.675 within the solid mass. Truth gas fraction0.01. Curves A/B have slopes30/40 K per ln(P/0.1bar), with pressure coverage0.1..1e10bar. Density EOS remains identical, temperature-dependent density is intended. The gas-base T also changes deeper-layer T continuously; this is coupled structure sensitivity. Gas/rock base is not an H/He-water boundary, and no physical RCB is inferred.

The earlier private contract used A20/B40. Before any full planet invocation, a thin-envelope planning estimate suggested recovery might lie outside the existing0.002..0.08 gas-fraction bracket; A was prospectively changed to30. The original contract hash and rationale are retained in the machine contract. No measured output informed this change. Thresholds, bracket and budget are unchanged.

Budget: at most20 full planet invocations including failures,120seconds per case, at most12 inverse iterations. Cases: unchanged OFF baseline, modified OFF same input, A/B forward truth, B tighter tolerances, A with collinear knot refinement, A recovery low/high endpoints, then at most12 bisections. Failed/unbracketed/unresolved cases must be recorded; do not tune thresholds to make them pass.

Rationale: normalized three-residual fit<=1e-6; actual gas T<=1e-12 and density<=1e-10 versus common evaluator/EOS; raw accepted pre-projection T<=1e-6; total mass<=1e-8 relative. OFF radius<=1e-12 relative. Tighter/refined radius difference<=2e-5 AND actual thermal signal at least10 times numerical change. Recovery stops on radius relative error<=1e-5 OR gas-fraction bracket width<=2e-5. These are software acceptance tolerances, not universal planetary accuracy.

Before each case, freeze build, config, profile and actual source-file SHA256 identities plus the untouched numeric contract hash in a new case directory. Capture stdout/stderr, exit code and time. Only after successful exit record the generated diagnostic SHA256. tests/check_tp_model.py requires matching build/config/profile/source/diagnostic artifact hashes and independently recomputes raw fitting residuals, T(logP), fixed-Gas density and gas mass membership. A sidecar alone is not proof of success. Existing eight-digit profile output is not used for1e-12 claims.

Two-node profiles exactly represent these linear-in-lnP curves. Collinear refinement checks knot handling, not curved-profile interpolation accuracy. All new outputs stay on D:; do not rerun historical54/8/67 grids or edit original research checkouts.

## Precision and execution handoff

The two OFF cases run the same tests/tp_off_probe.cpp compiled against the untouched baseline and current solver. It calls existing fitting_method without TP and exports actual full-precision radius/mass/status plus the unchanged legacy profile. Those are two full solver invocations inside the20-call cap, not extra runs. This verifies the solver OFF path; the full CLI OFF path is source-reviewed but is not separately executed under this budget. Eight-digit legacy profile bytes are compared as an additional compatibility check.

The Windows+WSL tests/run_tp_validation.py driver requires pre-existing current planet and both OFF probe builds. It does not install, authenticate, call providers or rebuild automatically. Use a new explicit output directory. Runtime acceptance additionally requires requested_gas_fraction per case and binds actual gas-base mass/measured fraction to it with the existing mass threshold, including inverse cases. Controller/checker/probe/template identities are frozen alongside scientific sources and inputs. Failures count and stop execution; no automatic code repair or budget extension.

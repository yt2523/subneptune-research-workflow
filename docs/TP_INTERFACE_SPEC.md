# Prescribed gas T(P): first implementation contract

Date: 2026-10-28. Status: implementation contract; Task1–3 engineering implementation is recorded in TP_IMPLEMENTATION_PROGRESS.md. Numerical/scientific acceptance is separate. This contract itself does not authorize model runs. Parent acceptance: [TP01–TP12](TP_ACCEPTANCE.md). Source audit: [call paths and provenance](TP_SOURCE_AUDIT.md).

## Purpose and limits

Change gas-layer T(P) while keeping the outer pressure/temperature, total mass, composition treatment and density EOS identical between comparison cases. Density may change because temperature changes; keeping the EOS fixed does not mean keeping density fixed.

This is prescribed-profile sensitivity, not a radiative–convective equilibrium solver, measured RCB, cooling evolution or moist H/He–water mixture model. Record P0, P_switch, P_rc (unknown unless independently established), and P_HHB separately. A changed gas-base temperature can change deeper-layer temperatures under existing temperature-jump conditions; record that coupled response rather than calling it a gas-only radius effect.

## First supported configuration

- Mode 0 only; four existing composition slots; nonzero atmosphere plus at least one non-gas layer. Gas-only models are rejected when the new interface is enabled.
- New optional string `tp_profile_file`; missing means OFF. Add `Settings::HasOption(const std::string&) const` to distinguish absence from malformed values; do not catch every parsing error and silently disable TP. Explicit empty value, wrong type or unreadable path is an error.
- New atmosphere selector `atm_phasedgm="gas_fixed_mu2"` always returns the existing `Gas` EOS for valid gas-layer P,T, without the 100-bar selector. Require this selector when TP is enabled. Existing selectors and OFF behavior remain unchanged. Reject this new selector without TP in v1 to avoid introducing an unreviewed additional thermal recipe.
- Reusing Gas (mmol=2, n=2) is a minimal engineering verification fixture, NOT an approved physical atmosphere for TOI-732 c. Do not alter the global Gas/Gas_iso parameters. A realistic H/He EOS and composition remain a separate physical choice before scientific comparisons.
- Resolve profile paths relative to the cfg directory; do not change existing legacy path semantics. The existing settings parser removes whitespace, including quoted whitespace: v1 rejects whitespace-containing TP paths explicitly rather than pretending to support them. Add a dedicated raw-value validation for this option before its path is normalized.
- Reject TP in other modes, absent/massless gas, negative/nonfinite masses, nonzero temperature jumps, and incompatible selectors. V1 requires all three jumps zero; nonzero jumps and skipped intermediate layers can be added later with their own tests. Zero-mass internal slots are otherwise supported using existing skip rules.

These restrictions are coordinator design choices, not claims of human approval of a planetary composition.

## File format, units and evaluator

UTF-8 ASCII-compatible CSV; exact first line `P_bar,T_K`, followed by at least two rows, exactly two numeric fields each. Allow blank lines and surrounding ASCII whitespace in data; no comments/extra columns. Strictly positive finite P and T; P strictly increasing; reject duplicates, trailing junk and incomplete rows. Temperature need not be monotone. Reject a UTF-8 BOM with a clear format error in v1.

Convert once on load: P_cgs = P_bar * 1e6 (dyn/cm², called microbar in the code); 1 GPa = 1e10 cgs. Reject overflow after conversion. Logarithms use a dimensionless pressure ratio, e.g. ln(P_cgs / 1 cgs).

For consecutive nodes (P_i,T_i), let b=(T_{i+1}-T_i)/ln(P_{i+1}/P_i). Evaluate T(P)=T_i+b ln(P/P_i) and dT/dP_cgs=b/P. No extrapolation, clamp or automatic rescaling. Endpoints are inclusive. At an internal knot choose the right interval derivative; at the last node use the left interval. Interpolation/round-trip assertions: absolute error <= 1e-12 * max(1,abs(reference)). This arithmetic test tolerance is not a planetary accuracy claim.

Outer boundary must be covered and `abs(T(P_surface)-surface_temp) <= 1e-12*max(1,abs(surface_temp))`; otherwise fail, do not shift the curve. Require coverage for EVERY actual gas evaluation, including trial RHS evaluations. Out-of-range evaluation invalidates that model attempt with the offending pressure/range recorded. Never silently use an EOS edge value or generate a replacement profile. Trials outside coverage may fail even when an intended final model would fit: report this limitation and extend the prescribed input deliberately before a new authorized run.

New module `src/tp_profile.h/.cpp` (C++11, standard library only):

```cpp
struct TPState { double temperature_K; double dT_dP_cgs; };
class TPProfile {
 public:
  static TPProfile load_csv(const std::string& path);
  TPState at_cgs(double pressure_cgs) const;
  double min_pressure_cgs() const;
  double max_pressure_cgs() const;
};
```

Load/lookup throw `std::runtime_error` with a useful reason. Catch lookup exceptions inside C/GSL callbacks, mark an explicit error in per-solve context and return GSL_EBADFUNC; never unwind through GSL. Catch input errors in main and exit nonzero before integration. Own the immutable profile in main for the whole solve; pass a non-owning `const TPProfile*` in solve/loop/RHS context. No mutable global active profile. Audit every context reset/aggregate initializer. Legacy callers get a default nullptr argument; old execution paths remain separate.

## Integration contract

Keep the current three-state system for compatibility; in prescribed gas segments use a single effective T=profile.at_cgs(P).temperature_K for ALL phase checks, density calls, accepted states, boundary storage and diagnostics. RHS dT/dx = (dT/dP_cgs)*(dP/dx), using the sign of the existing pressure equation in either direction. Do not additionally call entropy, dTdm or dTdP_S for a prescribed gas segment. The integrated temperature state is diagnostic there: compute its pre-projection mismatch, then project accepted gas states to the same evaluator and reset GSL state when projection or a knot/segment boundary requires it. Record the mismatch; do not hide integrator error by reporting only projected temperatures.

Stop gas steps at TP interpolation knots or demonstrate an equivalent knot-aware error control in tests before acceptance. This avoids allowing a derivative discontinuity to bypass the error estimate. Gas membership is the composition slot/mass interval and direction, not an EOS label substring or comparison of pressure with 100 bar. All non-gas layers keep their original EOS and thermal equations.

At the gas base, evaluate the gas-side temperature at the actual boundary pressure and pass it continuously to the first massive inner component (v1 jumps are zero). Never evaluate gas T(P) at solid-layer central pressure. Preserve the inner temperature integration and central Tc degree of freedom.

## Fitting restriction (essential)

Existing fitting solves Rp,Pc,Tc against radius, pressure and temperature residuals. If Mfit lies in prescribed gas, temperature matching can become a function of pressure matching, losing an independent equation. V1 therefore REJECTS any actual Mfit in or on the gas mass interval, including after the existing boundary-avoidance adjustment. Require `0 < Mfit < M_non_gas*ME` after that adjustment; no silent relocation or deletion of the temperature residual. Existing special fitting corrections may not manufacture acceptance: record their use and reject corrected/truncated branches as validated TP solutions in v1.

With Mfit strictly in non-gas material, the final inside-out fitting branch stays in non-gas material; the outer branch and Rloop must still carry the profile through gas. Test both gas RHS directions directly, but do not claim v1 solves a full planet whose inside-out branch crosses gas. Any future lifting of this restriction needs a fresh matching-condition design.

## Diagnostics and acceptance ownership

Enabled mode writes `<output_file>.tp.json` only after a successful model. Required fields: schema_version=1, status, source/build/config/profile identities supplied or recorded by controller, EOS selector and parameters, outer P/T, profile pressure bounds, min/max evaluated gas pressure, maximum accepted gas pressure, gas-base P/T and mass boundary, actual Mfit, fit residuals R/P/T, ode status, use of fitting corrections, max pre-projection T residual, max effective T residual and EOS density residual. The controller hashes the exact profile/config/build and diagnostic file; do not invent runtime hashes the program has not computed. Failed models exit nonzero, print reason and offending pressure; do not emit a success sidecar or reuse a previous one. Define density residual against `Gas->density(P,T_effective,...)`, not a second independently evolving temperature.

Raw diagnostic doubles use max_digits10. Do not change legacy profile output formatting (normally 8 significant digits); do not claim 1e-12 validation from rounded legacy output. No new acceptance threshold for planetary radius/mass/fit error is approved here. Before a numerical run, Codex must freeze a run contract with baseline build/config, baseline stability evidence, tolerances, resolution comparison and run budget. Reuse old evidence where applicable; do not rerun the 54/8/67 suites.

Coverage: TP01 OFF regressions; TP02/03 parser/evaluator; TP04/05 common effective T and callback checks; TP06 fixed EOS; TP07 fitting/boundary diagnostics; TP08 lookup failures; TP09 future numerical contract; TP10 composition recovery later; TP11 physical labels; TP12 isolated commits and provenance. All scientific gates remain NOT RUN.

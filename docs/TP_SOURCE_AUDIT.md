# TP read-only source audit — 2026-10-28

Audited shareable repo: main at 65b52ca770472de56e1b5fe68ccb9881db48a4b1; initially clean. `git diff 9e74aac -- src Makefile` empty. No source edits, build, provider calls or planet runs in this milestone. Report basis: local thermal-assumptions-report-20261026 REPORT.html, verification.json, scope-and-evidence.json; no fresh literature-verification claim.

## Call map (line numbers at audited revision)

| Path | Observation | Consequence |
|---|---|---|
| src/main.cpp:234–277,358–405 | Settings -> four composition slots -> mode0 fitting_method(...,false) | Add optional input without requiring old cfg changes; thread context through the actual mode0 entry |
| src/parser.cpp:34–64 | Parser strips all whitespace, including quotes; getters throw on missing/wrong type | Add HasOption; explicitly reject whitespace in new TP paths before stripping; do not hide malformed options |
| src/hydro.cpp:1539–1691;1498 | Rloop -> R_hydro -> outer-in hydro constructor | TP must be present already during radius shooting, not just final fitting |
| src/hydro.cpp:1699–1805 | fitting_error chooses Rp,Pc,Tc; 3 residuals; initial Mfit=0.2 Mtot then possible adjustment | Require final adjusted fitting mass below gas; otherwise prescribed T(P) can remove independent temperature matching |
| src/hydro.cpp:57–90;109–141 | derivs_m2/m3 use density(P,y[2]) then thermal equation; pressure derivative signs differ | Same effective T for density and thermal path; use dT/dP times the signed dP/dx |
| src/hydro.cpp:188–278;332–450 | Outer initialization, accepted states, phase updates and Tgap | RHS-only change misses initial/stored density and boundary temperatures |
| src/hydro.cpp:690–808 | Center and first-step initialization include density overload that updates T | Must remain legacy for non-gas center; gas-only case rejected in v1 |
| src/hydro.cpp:974–1022;1032–1121;1280–1319 | Temperature jumps, outer fitting initialization, mass-based fit corrections | Preserve continuity for zero jumps; record/reject corrected fits as accepted TP models |
| src/hydro.cpp:1342–1378 | Standard output mostly 8 significant digits, debug 16 | High-precision sidecar required for tight evaluator/density validation |
| src/hydro.h:75 onward | mass_params, loop_params contain EOS/component/temperature state, no TP pointer | Extend solve context and every constructor/reset/caller; do not use global active profile |
| src/phase.cpp:641–665 | gas_default and HHe_tabulated switch at P=1e8 cgs=100 bar | Neither selector isolates thermal shape when its switch is moved |
| src/EOSlist.cpp:462,525 | Gas mmol=2,n=2; Gas_iso mmol=3,n=0 | New fixed selector reuses one EOS throughout gas; never mutate shared default objects |
| src/EOS.cpp:1051–1144 | density takes cgs P; ideal density proportional to mmol*P/T | Fixed EOS still permits a physical density response to changing T |
| src/EOS.cpp:1757–1814 | dTdP_S takes GPa, returns K/GPa; tabular branch clamps some out-of-range slopes | TP callback derivative uses cgs units; no invoking/clamping original adiabatic path for prescribed gas |
| src/EOS.cpp:1854–1930 | density overload evolves temperature using an EOS path | Not interchangeable with a plain density(P,T) evaluation |
| src/phase.cpp:111–138 | Generic phase-boundary helper uses linear T(P), unlike new linear T(logP) | Fixed gas selector has no internal phase switch; do not reuse helper as arbitrary TP interpolation |
| Makefile:11–25 | src/*.cpp wildcard; C++0x; no existing test target | Standard-library TP module fits current language floor; separate narrow C++ test target |

Potential legacy inconsistencies seen, NOT repaired: hydro.cpp:333 evaluates new phase density at P[0] with current y[2]; hydro.cpp:808 uses Tt at layer entry; hydro.cpp:249 dereferences Phase before checking null. The enabled path must avoid inconsistent state and fail cleanly; changing unrelated OFF behavior requires a separate scoped fix. Source reading alone does not establish the numerical impact of these observations.

## Original repositories (read-only checks)

- Original Magrathea: branch 实验复现, HEAD 9e74aac2ccd62cd70102ce9dda922149afcb531b. Existing modified plot/README.md and run/mode0.cfg; untracked plot/COMPARE_PROFILES.md, compare_profiles.py, compare_profiles.sh, test_compare_profiles.py; result/mr_trends.log, mr_trends_manifest.csv; run/mode3_mr_trends.cfg. Preserved.
- Clean research worktree: workflow/mode0-inputs-20261025, same 9e74aac full hash, clean.
- mode0-workbench: fix/tp-wrapper-mode0, HEAD 240a6415339a1fe2f103394283580429f6279e49, clean.

Native Git initially could not enter the original D: directories under the sandbox. Explicit read-only commands succeeded with escalation; no originals were granted write access or changed. The shared repository alone was granted turn-scoped write access for documentation.

Machine-readable byte hashes and final documentation checks: `tp-stage1-verification.json` (generated after review). Hashes identify local bytes; Git text normalization may change documentation bytes in a fresh checkout.

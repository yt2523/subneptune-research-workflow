# Scientific engineering and archived experiments

The runnable MAGRATHEA source and tabulated dependencies are at repository root. Upstream MIT attribution is in LICENSE; author and references are in docs/MAGRATHEA_UPSTREAM_README.md. Source baseline before packaging: 9e74aac. No C++ science edits in this release.

## Reading results without running anything

Open experiments/subneptune-20261027/outputs/thermal-composition-20261025-b01/REPORT.md, verification.json, independent_numeric_checks.json, delivery_state.json. Two earlier output directories have corresponding reports. Historical SHA256SUMS.json preserves original bytes, including cfg/profile/stdout/checks. Original absolute D:/ paths in manifests record provenance; they are not portable launch configuration.

## Rebuilding (when you explicitly choose)

On Linux/WSL with g++ / make / GSL already present:

```sh
make -B -j2
```

Run solver with cwd at repository root to find tabulated files. Never assume a binary copied from a different checkout matches source. Compare source/compiler/config/binary identities and numerical baselines before new science. Windows workflow Python does not remove the need for Linux/WSL solver dependencies.

## Existing mode0 driver (explicit paths)

The archived Python driver already supports portable explicit inputs. Example only, NOT run during packaging:

```sh
python3 experiments/subneptune-20261027/tooling/mode0_batch.py   --repo "$PWD"   --table experiments/subneptune-20261027/tooling/demo_cases.csv   --template run/mode0.cfg   --output "$PWD/.runs/science-new-batch" --limit 1
```

Validate template EOS/units and choose a fresh output before running. Pressure input is microbar, temperature K, layer masses Earth masses. Driver output finite/boundary checks are not internal convergence certification. Historical followup_comparisons.py / verify_followup.py retain original machine paths and are archived execution/provenance tools, not the new portable workflow entry. Do not run them blindly to reproduce all 67 evaluations. For a full numeric replay, first port their path configuration in a separately reviewed task; plotting additionally needs scientific Python dependencies.

## Research limitations

5 and 8.04 Earth masses are synthetic examples. Boundary-temperature studies affect continuous solid-layer temperatures too. Gas_default has a mu transition at 100 bar. HHe_tabulated comparison changes whole atmospheric prescription. Gray profiles are prescribed sensitivity cases, not RCE ground truth. Full TP import, new composition posterior, chemistry and evolution are not implemented by this packaging release.

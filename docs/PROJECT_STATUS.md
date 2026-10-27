# Current project state / 当前状态

As of 2026-10-27. Synthetic cases, no selected observed planet.

Completed historical research: 54 semi-grey evaluations; 8 mode0 validation runs; 67 temperature-boundary/composition-recovery evaluations. See experiments/subneptune-20261027/outputs/ and original reports. Baseline solver source 9e74aac; tooling 240a641. No C++ science changes made for this packaging release.

Next scientific milestone: read-only map of T(P), density, bidirectional integration and fit paths, then optional default-off TP input specification. Do not move gas_default's 100 bar phase boundary to create a purported pure thermal experiment: it changes molar mass 3→2 as well as thermal behavior.

Ordered gates: TP acceptance contract → default regression → analytic prescribed-TP validation → same-boundary/same-density-EOS small comparison → resolution/tolerance/base-pressure coverage → synthetic composition recovery. Physical choices must be recorded before implementation; existing code does not solve full RCE or chemistry.

Packaging release implements infrastructure and offline workflow demonstration only. Read docs/workflow/RELEASE_VERIFICATION.md for fresh results and untested boundaries. No new planet simulations authorized merely by cloning or running doctor.

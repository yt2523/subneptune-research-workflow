# Current project state / 当前状态

As of 2026-10-27. Synthetic cases, no selected observed planet.

Completed historical research: 54 semi-grey evaluations; 8 mode0 validation runs; 67 temperature-boundary/composition-recovery evaluations. See experiments/subneptune-20261027/outputs/ and original reports. Baseline solver source 9e74aac; tooling 240a641. No C++ science changes made for this packaging release.

Next scientific milestone: read-only map of T(P), density, bidirectional integration and fit paths, then optional default-off TP input specification. Do not move gas_default's 100 bar phase boundary to create a purported pure thermal experiment: it changes molar mass 3→2 as well as thermal behavior.

2026-10-28 Stage 1: [read-only audit](TP_SOURCE_AUDIT.md), [interface contract](TP_INTERFACE_SPEC.md) and [bounded DeepSeek task plan](superpowers/plans/2026-10-28-prescribed-tp.md) prepared. Fresh builder-readability review found no material unanswered design question; this is not code or numerical acceptance. Full TP interface remains NOT IMPLEMENTED. V1 proposes a fixed-mu=2 ideal-gas verification fixture and requires the actual fitting point below the gas layer; target-planet atmosphere choice and numerical run thresholds remain open. Next action: review the Stage 1 contract before authorizing implementation/provider calls. No new scientific runs.

Ordered gates: TP acceptance contract → default regression → analytic prescribed-TP validation → same-boundary/same-density-EOS small comparison → resolution/tolerance/base-pressure coverage → synthetic composition recovery. Physical choices must be recorded before implementation; existing code does not solve full RCE or chemistry.

Packaging release implements infrastructure and offline workflow demonstration only. Read docs/workflow/RELEASE_VERIFICATION.md for fresh results and untested boundaries. No new planet simulations authorized merely by cloning or running doctor.

2026-10-28 implementation update: Task1 profile/configuration infrastructure implemented and independently reviewed; see [execution ledger](TP_IMPLEMENTATION_PROGRESS.md) and tp-task1-verification.json. Full TP solver interface remains incomplete; active TP inputs deliberately stop before integration. Human authorized continued dependent stages in this session; no new target-planet physical assumptions are implied.

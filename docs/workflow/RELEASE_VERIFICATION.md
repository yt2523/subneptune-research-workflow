# Release verification — 2026-10-27

Final portable runner SHA256: `3cc1bc4f213c1d2ff9fc47055daed7679d1415b55dbb457389cd42733cd190b3`.

- Windows Python 3.12.10: **66 tests passed**, 4 privilege/platform skips; see [raw test output](evidence/windows.log).
- WSL Python 3.14.4: **66 tests passed**, 2 Windows-specific skips; see [raw test output](evidence/linux.log). Linux actually exercises source/destination symlink sentinel checks.
- [Independent review](INDEPENDENT_REVIEW.md): real early request-changes preserved in summary; final scoped approval resolves identified blockers.
- Original archive inventory: **689 file hashes unchanged**. Scientific src/, tabulated/ and Makefile match baseline 9e74aac. No new planet experiment, compiler installation, provider login or credential migration performed.
- Public-file scan: no credentials files or common real-key/private-key patterns found. This is a bounded scan, not a mathematical guarantee.

The new runtime's provider adapters have mocked regression coverage, including rejection/repair, budget, strict reviewer output, stale-file rejection and redirect handling. This packaging run did not perform a real DeepSeek→new-runtime→Codex end-to-end job; development itself used the already configured real DeepSeek/Cline service. Colleagues must provide their own valid API access / reviewer configuration. Offline fixture success is not live-provider success or scientific validation.

Fresh local clone + doctor + three-node offline execution/resume verification is the next packaging gate; its evidence will be appended before public release. GitHub CI configuration is supplied but remote CI outcome is not asserted by these local tests.

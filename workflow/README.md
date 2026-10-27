# Portable workflow

Start at repository README.md. Supported new entry: `python workflow/portable.py`.

- `portable.py`: self-contained standard-library runtime; configuration comes from examples/demo.json or your local config.
- `tests/`: current infrastructure acceptance tests.
- `examples/`: no-key demo.
- `legacy/`: original Windows/Cline controller, preserved for provenance; not a portable launch entry.
- Original Store source and its tests remain together under `legacy/`; portable runner is standalone.

Roles and permissions: ../AGENTS.md. API file setup: ../docs/workflow/SETUP.md. TP scientific acceptance is separate from workflow infrastructure acceptance. Never launch a planetary grid merely because offline tests pass.

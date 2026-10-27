# Provenance and design references

- MAGRATHEA: https://github.com/Huang-CL/Magrathea (MIT), yt2523/Magrathea experimental fork. Preserve upstream LICENSE and scientific attribution.
- Historical research branch: yt2523/Magrathea archive/subneptune-20261027 at 0aa6316c66c126bd405f9008bf346eeb8ddf2d37. Three output archives and SHA inventory copied unchanged.
- Original local workflow: workflow/setup at e9b6cd7, copied tracked source into workflow/legacy without runs/logs/credentials; historical source only. New portable path avoids its hard-coded Windows locations.
- Reference project: https://github.com/mewamew/huaizi-de-cows ; informed separate builder/reviewer roles, externally fixed acceptance and concise experience rules. No game assets or implementation imported.
- OpenAI, Run long horizon tasks with Codex (2026-02-23): https://developers.openai.com/blog/run-long-horizon-tasks-with-codex ; milestones, executable checks and durable status.
- OpenAI, Rethinking skills and prompts (2026-09-11): https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra ; narrow task-triggered context.
- Anthropic, Harness design (2026-03-24): https://www.anthropic.com/research/harness-design-long-running-apps ; independent evaluation and structured handoff.
- Planning with Files: https://github.com/OthmanAdi/planning-with-files ; durable planning inspiration only, not installed or copied as a runtime dependency.
- DeepSeek official API: https://api-docs.deepseek.com/ ; configured HTTPS chat-compatible endpoint. Codex noninteractive: https://developers.openai.com/codex/noninteractive .

New workflow code is authored by DeepSeek under Codex task specification; Codex reviews and executes independent verification. Actual release results belong in RELEASE_VERIFICATION.md. No claim that references independently validate this implementation or its science.

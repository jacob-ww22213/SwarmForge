# Changelog

This project follows a lightweight SemVer-style versioning scheme while the product is still pre-1.0:

- `MAJOR`: breaking architecture or workflow changes
- `MINOR`: new user-facing features, new system capabilities, or major demo upgrades
- `PATCH`: bug fixes, documentation fixes, test-only changes, or small UX improvements

Current version:
- `0.5.0`

## [0.5.0] - 2026-03-29

Added:
- dual-role distributed console with project-side and user-side views
- stage-3 distributed controller and worker MVP
- distributed MoE routing and two-round MoA collaboration flow
- Codex skill for launching the distributed demo
- bilingual GitHub documentation with controller / worker / Ollama run flow
- local versioning and release support files
- one-click local demo scripts for start, health check, and stop

Changed:
- the distributed web page is now a product-oriented console instead of a controller-only debug page
- task history now records the requester role
- project documentation now explains model download, worker startup, and online heartbeat requirements

Verified:
- automated test suite passing locally
- local controller + worker smoke tests for project-side and user-side task submission

## [0.4.0] - 2026-03-29

Added:
- distributed controller, worker, and shared helper layer
- browser dashboard for worker visibility, task dispatch, and distributed results
- distributed task persistence and metrics

## [0.3.0] - 2026-03-29

Added:
- web demo with result viewing and history replay
- single-model baseline comparison in the browser UI

## [0.2.0] - 2026-03-29

Added:
- modular project structure for `core/`, `providers/`, `experts/`, and `reporting/`
- B-line expert modules and reporting modules

## [0.1.0] - 2026-03-29

Added:
- initial SwarmForge / SwarmOS demo foundation
- CLI flow, docs, examples, and early outputs

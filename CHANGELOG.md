# Changelog

This project follows a lightweight SemVer-style versioning scheme while the product is still pre-1.0:

- `MAJOR`: breaking architecture or workflow changes
- `MINOR`: new user-facing features, new system capabilities, or major demo upgrades
- `PATCH`: bug fixes, documentation fixes, test-only changes, or small UX improvements

Current version:
- `0.7.0`

## [0.7.0] - 2026-03-30

Changed:
- moved distributed execution from controller callback mode to a worker-pull task queue so NATed nodes can still execute tasks without exposing a reachable public inference port
- tightened node readiness so a worker is only marked `READY` after heartbeat, task-pull connectivity, and local provider self-check all pass
- added callback reachability diagnostics against `/api/status`; callback failures are now shown as a red degraded signal instead of being mistaken for execution readiness
- updated the browser console to block task submission when there are no `READY` nodes and to explain the new readiness signals directly in the worker cards

## [0.6.5] - 2026-03-30

Changed:
- removed the distributed UI history task panel so the page focuses on current node onboarding, current run status, and the active task result only
- stopped the browser from fetching and rendering saved task history during normal page refreshes
- kept direct task execution and post-run rating intact while simplifying the console layout

## [0.6.4] - 2026-03-30

Changed:
- turned the distributed node onboarding area into a guided UI with editable controller IP, node IP, port, model, and worker identity fields
- added generated bootstrap, repo-local skill, manual worker, and post-check commands that can be copied directly from the browser
- connected recommended model cards to the onboarding wizard so choosing a model updates the generated commands automatically

## [0.6.3] - 2026-03-30

Changed:
- added a bootstrap script for brand-new remote node machines that clones the repo, prepares a venv, and starts an Ollama worker
- updated docs to explain that `swarmforge-demo-runner` is a repo-local skill and cannot be used before the repository exists locally

## [0.6.2] - 2026-03-30

Changed:
- fixed cross-machine node onboarding docs and scripts so remote users no longer default to `127.0.0.1` for the controller URL
- updated the distributed web page to explain `CONTROLLER_IP` and `NODE_PUBLIC_IP` explicitly for remote workers
- added environment-variable overrides to the bundled worker startup scripts for remote controller and node-public-address configuration

## [0.6.1] - 2026-03-29

Changed:
- simplified the distributed front-end by removing the role switcher and hiding internal demo worker ids from the main UI
- moved model onboarding to recommended-model cards that open official Ollama model pages and provide copyable `ollama pull` commands
- updated docs to clarify the intended architecture: the server hosts the controller, while users download and run small models on their own nodes
- stopped the server-side demo workers so the public controller now reflects the controller-only product shape by default

## [0.6.0] - 2026-03-29

Added:
- Linux `systemd` deployment assets for controller, worker instances, firewall bootstrap, and full demo target
- server-side install script for persistent systemd deployment

Changed:
- switched the deployed server from mock workers to real Ollama-backed workers using `qwen2.5:0.5b`
- made controller and worker HTTP servers threaded so long requests no longer freeze the whole UI
- tightened worker token defaults for low-core CPU deployments and increased request/pull timeouts for Ollama operations
- improved the front-end model download controls so non-Ollama nodes are disabled and request failures are shown in the status bar
- hardened log handlers to avoid crashes on unusual request logging paths

## [0.5.1] - 2026-03-29

Changed:
- made local release scripts portable by resolving the repository root dynamically instead of using a machine-specific absolute path
- made Codex skill helper scripts portable for multi-machine and server use
- switched release and helper scripts from zsh-specific entrypoints to portable bash entrypoints for Linux deployment
- hardened trace loading to ignore AppleDouble metadata files copied from macOS archives

Verified:
- automated tests passing locally
- local health-check flow passing against running controller and worker services
- remote deployment, remote test suite, and public controller health check passing on Ubuntu

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

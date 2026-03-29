---
name: swarmforge-demo-runner
description: Start, verify, and stop the SwarmForge distributed demo. Use this when the user wants to launch the controller, start local mock or Ollama workers, verify the web demo, or stop the local demo processes after testing.
---

# SwarmForge Demo Runner

Use this skill when the user wants to run the SwarmForge distributed demo from this repository.

## What this skill does

- starts the controller
- starts one or more workers
- supports `mock` workers for quick demos
- supports `ollama` workers for real local models
- checks the controller and worker APIs
- stops the local demo processes when requested

## Workflow

1. Work from the repository root.
2. Prefer the bundled scripts in `scripts/`.
3. For the fastest demo, start:
   - one controller on port `8010`
   - one mock coding worker on port `8021`
   - one mock research worker on port `8022`
4. Verify with:
   - `GET /api/controller/status`
   - `GET /api/workers`
5. Tell the user to open `http://127.0.0.1:8010`.

## Commands

- Start controller:
  `./.codex/skills/swarmforge-demo-runner/scripts/start_controller.sh`
- Start mock coding worker:
  `./.codex/skills/swarmforge-demo-runner/scripts/start_mock_worker.sh coding`
- Start mock research worker:
  `./.codex/skills/swarmforge-demo-runner/scripts/start_mock_worker.sh research`
- Start Ollama worker:
  `./.codex/skills/swarmforge-demo-runner/scripts/start_ollama_worker.sh worker-a "Worker-A" coding_worker "Coding Worker" qwen2.5:7b 8021`
- Check local demo:
  `./.codex/skills/swarmforge-demo-runner/scripts/check_local_demo.sh`
- Stop local demo:
  `./.codex/skills/swarmforge-demo-runner/scripts/stop_local_demo.sh`

## Defaults

- repository root:
  `/Users/jacob/Documents/cursor/0.5b 模型的畅想`
- controller:
  `127.0.0.1:8010`
- mock workers:
  `127.0.0.1:8021` and `127.0.0.1:8022`

## Notes

- Use `mock` workers unless the user explicitly asks for real local models.
- Use the Ollama script only when the machine already has Ollama running on `http://127.0.0.1:11434`.
- If the user wants a presentation demo, start the controller and two mock workers, then verify the APIs and point them to the browser URL.

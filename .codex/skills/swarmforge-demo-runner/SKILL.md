---
name: swarmforge-demo-runner
description: Download or activate a local small model, start the SwarmForge controller and Ollama or mock workers, verify that worker nodes stay online, and stop the local demo when testing is complete.
---

# SwarmForge Demo Runner

Use this skill when the user wants to run the SwarmForge distributed demo from this repository.

## What this skill does

- starts the controller
- starts one or more workers
- supports `mock` workers for quick demos
- supports `ollama` workers for real local models
- helps the user understand how to pull a model and keep the worker online
- checks the controller and worker APIs
- stops the local demo processes when requested

## Workflow

1. Work from the repository root.
2. Prefer the bundled scripts in `scripts/`.
3. If the user wants a real local model:
   - make sure Ollama is already installed
   - make sure Ollama is running on `http://127.0.0.1:11434`
   - if the controller is on another machine, set `CONTROLLER_URL=http://<controller-ip>/`
   - set `PUBLIC_HOST=<this-node-ip>` so the controller can call the worker back
   - do not use `127.0.0.1` for `CONTROLLER_URL` on a different machine
4. For the fastest demo, start:
   - one controller on port `8010`
   - one mock coding worker on port `8021`
   - one mock research worker on port `8022`
5. Verify with:
   - `GET /api/controller/status`
   - `GET /api/workers`
6. For the shared remote demo, tell the user to open `http://31.97.191.47/`. Only use `http://127.0.0.1:8010` when they are running the full demo locally on the same machine.

## Commands

- Start controller:
  `./.codex/skills/swarmforge-demo-runner/scripts/start_controller.sh`
- Start mock coding worker:
  `./.codex/skills/swarmforge-demo-runner/scripts/start_mock_worker.sh coding`
- Start mock research worker:
  `./.codex/skills/swarmforge-demo-runner/scripts/start_mock_worker.sh research`
- Start Ollama worker:
  `CONTROLLER_URL=http://31.97.191.47/ PUBLIC_HOST=<this-node-ip> ./.codex/skills/swarmforge-demo-runner/scripts/start_ollama_worker.sh my-node-1 "My Node" coding_worker "Coding Worker" qwen2.5:0.5b 8021`
- Check local demo:
  `./.codex/skills/swarmforge-demo-runner/scripts/check_local_demo.sh`
- Stop local demo:
  `./.codex/skills/swarmforge-demo-runner/scripts/stop_local_demo.sh`

## Online worker runbook

When the user wants the node to stay online, explain the lifecycle clearly:

1. start Ollama
2. start the worker
3. keep both processes running
4. verify the worker is visible in the controller dashboard

For a quick explanation, tell the user:

- the model itself is served by Ollama
- the project sees the model only through the worker process
- the worker stays online only while both Ollama and the worker process are still running

If the user asks how to keep it alive, recommend one of:

- keep the controller and worker in separate terminal tabs
- use `tmux` or `screen`
- or run them under `nohup` / a process manager if they want longer-lived local testing

Example manual commands:

```bash
ollama serve
```

```bash
ollama pull qwen2.5:0.5b
```

```bash
CONTROLLER_URL=http://31.97.191.47/ \
PUBLIC_HOST=<this-node-ip> \
WORKER_BIND_HOST=0.0.0.0 \
./.codex/skills/swarmforge-demo-runner/scripts/start_ollama_worker.sh \
  my-node-1 "My Node" coding_worker "Coding Worker" qwen2.5:0.5b 8021
```

## Defaults

- repository root:
  `/Users/jacob/Documents/cursor/0.5b 模型的畅想`
- controller:
  shared remote demo: `31.97.191.47/`
  local dev only: `127.0.0.1:8010`
- mock workers:
  `127.0.0.1:8021` and `127.0.0.1:8022`

## Notes

- Use `mock` workers unless the user explicitly asks for real local models.
- Use the Ollama script only when the machine already has Ollama running on `http://127.0.0.1:11434`.
- If the user wants a presentation demo, start the controller and two mock workers, then verify the APIs and point them to the browser URL.
- If the user wants a real-model demo, explain that "download model" and "worker online" are two different steps: Ollama hosts the model, while the SwarmForge worker keeps the node registered and available.
- For cross-machine node onboarding, always remind the user that `127.0.0.1` means "this computer", not the remote controller.

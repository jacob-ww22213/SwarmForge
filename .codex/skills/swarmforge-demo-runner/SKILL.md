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
   - start the worker first so it can register with the controller
   - then pull or switch the model from the dashboard, or use `ollama pull` separately
4. For the fastest demo, start:
   - one controller on port `8010`
   - one mock coding worker on port `8021`
   - one mock research worker on port `8022`
5. Verify with:
   - `GET /api/controller/status`
   - `GET /api/workers`
6. Tell the user to open `http://127.0.0.1:8010`.

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
ollama pull qwen2.5:7b
```

```bash
python3 -m swarmos_demo.worker \
  --controller-url http://127.0.0.1:8010 \
  --public-url http://127.0.0.1:8021 \
  --host 127.0.0.1 \
  --port 8021 \
  --provider ollama \
  --base-url http://127.0.0.1:11434/v1 \
  --model qwen2.5:7b \
  --worker-id worker-a \
  --name Worker-A \
  --role-key coding_worker \
  --role-name "Coding Worker"
```

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
- If the user wants a real-model demo, explain that "download model" and "worker online" are two different steps: Ollama hosts the model, while the SwarmForge worker keeps the node registered and available.

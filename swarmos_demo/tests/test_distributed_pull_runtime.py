from __future__ import annotations

from controller import ControllerState
from worker import WorkerRuntime


class _Args:
    worker_id = "node-1"
    name = "Node 1"
    role_key = "coding_worker"
    role_name = "Coding Worker"
    provider = "mock"
    model = "mock-model"
    base_url = None
    api_key = None
    controller_url = "http://controller:8010"
    host = "0.0.0.0"
    port = 8021
    public_url = "http://127.0.0.1:8021"
    heartbeat_interval = 5
    pull_interval = 1
    pull_timeout = 5
    temperature = 0.2
    max_tokens = 512


def test_controller_state_requires_pull_and_provider_health_for_ready() -> None:
    state = ControllerState(stale_after_s=20)
    state.upsert_worker(
        {
            "worker_id": "node-1",
            "name": "Node 1",
            "role_key": "coding_worker",
            "role_name": "Coding Worker",
            "provider": "ollama",
            "model": "qwen2.5:0.5b",
            "public_url": "http://node-1:8021",
            "provider_ready": True,
        }
    )
    worker = state.list_workers()[0]
    assert worker["heartbeat_online"] is True
    assert worker["pull_online"] is False
    assert worker["ready"] is False

    state.mark_worker_pull("node-1")
    worker = state.list_workers()[0]
    assert worker["pull_online"] is True
    assert worker["ready"] is True

    state.upsert_worker(
        {
            "worker_id": "node-1",
            "name": "Node 1",
            "role_key": "coding_worker",
            "role_name": "Coding Worker",
            "provider": "ollama",
            "model": "qwen2.5:0.5b",
            "public_url": "http://node-1:8021",
            "provider_ready": False,
            "provider_error": "model missing",
        }
    )
    worker = state.list_workers()[0]
    assert worker["provider_ready"] is False
    assert worker["ready"] is False


def test_controller_state_queue_roundtrip_collects_worker_result() -> None:
    state = ControllerState(stale_after_s=20)
    state.upsert_worker(
        {
            "worker_id": "node-1",
            "name": "Node 1",
            "role_key": "coding_worker",
            "role_name": "Coding Worker",
            "provider": "mock",
            "model": "mock-model",
            "public_url": "http://node-1:8021",
            "provider_ready": True,
        }
    )

    assignment = {
        "assignment_id": "assign-1",
        "task_id": "task-1",
        "worker_id": "node-1",
        "worker": {"worker_id": "node-1", "name": "Node 1"},
        "task": "review this change",
        "mode": "proposal",
        "round_index": 1,
        "routing_score": 0.88,
        "peer_results": [],
    }
    state.enqueue_assignments([assignment])
    pulled = state.next_assignment("node-1", wait_timeout_s=0.01)
    assert pulled is not None
    assert pulled["assignment_id"] == "assign-1"

    state.submit_task_result(
        "task-1",
        "assign-1",
        {
            "assignment_id": "assign-1",
            "worker_id": "node-1",
            "status": "ok",
            "proposal": {"summary": "done", "recommendations": [], "risks": [], "confidence": 0.9},
        },
    )
    results = state.await_task_results("task-1", ["assign-1"], timeout_s=0.01)
    assert results["assign-1"]["status"] == "ok"


def test_mock_worker_runtime_health_is_ready() -> None:
    runtime = WorkerRuntime(_Args())
    ready, error, models = runtime.refresh_provider_health(force=True)
    assert ready is True
    assert error is None
    assert models == []

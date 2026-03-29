from __future__ import annotations

from distributed_common import (
    aggregate_distributed_results,
    build_distributed_metrics,
    build_worker_expert_profile,
    dedupe_keep_order,
    ollama_api_root,
    resolve_template_expert_key,
)


def test_ollama_api_root_strips_v1():
    assert ollama_api_root("http://127.0.0.1:11434/v1") == "http://127.0.0.1:11434"


def test_dedupe_keep_order_preserves_first_seen():
    assert dedupe_keep_order(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_build_worker_expert_profile_uses_worker_metadata():
    profile = build_worker_expert_profile(
        {
            "worker_id": "node-1",
            "name": "GPU-Node-1",
            "role_key": "coding_worker",
            "role_name": "Coding Worker",
            "model": "qwen2.5:7b",
            "temperature": 0.3,
            "max_tokens": 768,
        }
    )
    assert profile.key == "coding_engineer"
    assert profile.name == "GPU-Node-1"
    assert profile.max_tokens == 768


def test_resolve_template_expert_key_maps_known_roles():
    assert resolve_template_expert_key({"role_key": "research_worker"}) == "research_scientist"
    assert resolve_template_expert_key({"role_name": "Systems Worker"}) == "systems_architect"


def test_aggregate_distributed_results_builds_summary_and_lists():
    results = [
        {
            "status": "ok",
            "worker": {"name": "node-a"},
            "proposal": {
                "recommendations": ["keep trace", "add metrics"],
                "risks": ["latency"],
                "confidence": 0.8,
            },
        },
        {
            "status": "ok",
            "worker": {"name": "node-b"},
            "proposal": {
                "recommendations": ["add metrics", "retry failed nodes"],
                "risks": ["latency", "partial failure"],
                "confidence": 0.9,
            },
        },
    ]
    aggregate = aggregate_distributed_results("test task", results)
    assert "2 returned successful proposals" in aggregate["final_summary"]
    assert aggregate["top_recommendations"][0] == "keep trace"
    assert "partial failure" in aggregate["top_risks"]


def test_build_distributed_metrics_computes_completion_and_rating():
    results = [
        {"status": "ok", "latency_ms": 110, "proposal": {"confidence": 0.8}},
        {"status": "error", "latency_ms": 90},
        {"status": "ok", "latency_ms": 150, "proposal": {"confidence": 0.9}},
    ]
    metrics = build_distributed_metrics(
        results,
        controller_total_ms=320,
        online_worker_count=3,
        user_rating=4,
    )
    assert metrics["completed_worker_count"] == 2
    assert metrics["completion_rate"] == 0.667
    assert metrics["user_rating"] == 4

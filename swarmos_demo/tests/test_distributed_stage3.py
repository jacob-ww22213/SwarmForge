from __future__ import annotations

from distributed_common import (
    aggregate_distributed_results,
    build_review_task_prompt,
    build_distributed_metrics,
    build_worker_expert_profile,
    dedupe_keep_order,
    ollama_api_root,
    resolve_template_expert_key,
    route_workers,
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
    proposal_results = [
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
    review_results = [
        {
            "status": "ok",
            "worker": {"name": "node-review"},
            "proposal": {
                "recommendations": ["add metrics", "retry failed nodes"],
                "risks": ["partial failure"],
                "confidence": 0.93,
            },
        }
    ]
    aggregate = aggregate_distributed_results("test task", proposal_results, review_results)
    assert "第 1 轮节点" in aggregate["final_summary"]
    assert aggregate["top_recommendations"][0] == "add metrics"
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


def test_route_workers_prefers_coding_for_code_task_and_reviewer_for_round_two():
    workers = [
        {
            "worker_id": "coding-a",
            "name": "Coding A",
            "role_key": "coding_worker",
            "role_name": "Coding Worker",
            "keywords": ["code", "api"],
        },
        {
            "worker_id": "research-b",
            "name": "Research B",
            "role_key": "research_worker",
            "role_name": "Research Worker",
            "keywords": ["benchmark", "evaluate"],
        },
        {
            "worker_id": "planner-c",
            "name": "Planner C",
            "role_key": "planner_worker",
            "role_name": "Planner Worker",
            "keywords": ["plan", "mvp"],
        },
    ]
    proposal = route_workers("请做一个代码评审 demo，并输出测试建议", workers, phase="proposal", top_k=2)
    assert proposal["selected"][0]["worker_id"] == "coding-a"

    review = route_workers(
        "请做一个代码评审 demo，并输出测试建议",
        workers,
        phase="review",
        top_k=1,
        exclude_worker_ids={"coding-a"},
        prior_results=[{"proposal": {"summary": "round 1", "recommendations": ["add tests"], "risks": ["latency"]}}],
    )
    assert review["selected"][0]["worker_id"] == "research-b"


def test_build_review_task_prompt_includes_round_one_context():
    prompt = build_review_task_prompt(
        "review this payment flow",
        [
            {
                "worker_name": "node-a",
                "role_name": "Coding Worker",
                "summary": "Need stronger tests",
                "recommendations": ["Add integration tests"],
                "risks": ["Missing rollback"],
            }
        ],
    )
    assert "第 2 轮" in prompt
    assert "Add integration tests" in prompt

from __future__ import annotations

import argparse
from pathlib import Path

from core.storage import save_markdown, save_trace
from core.workflow import run_demo
from providers.base import ProviderError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SwarmOS routed multi-expert demo.")
    parser.add_argument("--task", help="Inline task text.")
    parser.add_argument("--task-file", help="Path to a UTF-8 text file with the task.")
    parser.add_argument(
        "--provider",
        choices=("mock", "openai-compatible", "ollama"),
        default="mock",
        help="Inference backend. Default is offline mock.",
    )
    parser.add_argument("--base-url", help="Base URL for openai-compatible or ollama providers.")
    parser.add_argument("--api-key", help="API key for openai-compatible provider.")
    parser.add_argument("--model", help="Model name for real providers.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of non-planner experts to route to.")
    parser.add_argument("--baseline", action="store_true", help="Also run a single-model baseline for comparison.")
    parser.add_argument("--update-reputation", action="store_true", help="Update expert reputation scores after this run.")
    parser.add_argument("--learn", action="store_true", help="Rebuild learned routing scores from all saved traces.")
    parser.add_argument("--save-markdown", help="Write the markdown report to this path.")
    parser.add_argument("--save-json", help="Write the JSON trace to this path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_demo(args)
    except (ValueError, ProviderError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(result["console_report"])

    if getattr(args, "learn", False):
        from core.learned_router import update_learned_scores
        from core.router import reload_learned
        scores = update_learned_scores()
        reload_learned()
        print(f"\nLearned routing scores updated ({len(scores)} experts).")

    if args.save_markdown:
        save_markdown(args.save_markdown, result["markdown_report"])
        print(f"\nSaved markdown report to {Path(args.save_markdown).resolve()}")

    if args.save_json:
        save_trace(args.save_json, result["trace"])
        print(f"Saved JSON trace to {Path(args.save_json).resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

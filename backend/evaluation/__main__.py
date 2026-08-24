"""Clean-checkout command for deterministic evaluation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from evaluation.adapter import EvaluationArtifactError
from evaluation.agent_runner import run_agent_evaluation
from evaluation.runner import run_evaluation


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m evaluation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument(
        "--dataset", required=True, choices=("development", "demonstration", "held-out")
    )
    agent = subparsers.add_parser("agent-evaluate")
    agent.add_argument(
        "--dataset", required=True, choices=("development", "demonstration", "held-out")
    )
    agent.add_argument("--runtime-export", required=True)
    agent.add_argument("--output-dir", required=True)
    agent.add_argument("--repository-root", default=None)
    evaluate.add_argument("--output-dir", required=True)
    evaluate.add_argument(
        "--repository-root",
        default=None,
        help="repository root; defaults to the checkout containing backend/evaluation",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repository_root = (
        Path(args.repository_root).resolve()
        if args.repository_root
        else Path(__file__).resolve().parents[2]
    )
    try:
        if args.command == "evaluate":
            run = run_evaluation(
                repository_root=repository_root,
                dataset=args.dataset,
                output_dir=Path(args.output_dir).resolve(),
            )
        else:
            run = run_agent_evaluation(
                repository_root=repository_root,
                dataset=args.dataset,
                output_dir=Path(args.output_dir).resolve(),
                runtime_export_path=Path(args.runtime_export).resolve(),
            )
    except (EvaluationArtifactError, OSError, TypeError, ValueError) as error:
        print(f"evaluation failure: {error}", file=sys.stderr)
        return 2
    if args.command == "evaluate":
        print(f"metrics: {run.report_path}")
        print(f"summary: {run.summary_path}")
        print(f"runtime result: {run.runtime_result_path}")
        return 0 if run.applicable_gates_passed else 1
    print(f"agent metrics: {run.metrics_path}")
    print(f"agent summary: {run.summary_path}")
    print(f"agent runtime export: {run.runtime_export_path}")
    return 0 if run.zero_false_clear_gate_status != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

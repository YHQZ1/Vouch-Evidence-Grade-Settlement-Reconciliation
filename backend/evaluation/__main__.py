"""Clean-checkout command for deterministic evaluation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from evaluation.adapter import EvaluationArtifactError
from evaluation.runner import run_evaluation


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m evaluation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument(
        "--dataset", required=True, choices=("development", "demonstration", "held-out")
    )
    evaluate.add_argument("--output-dir", required=True)
    evaluate.add_argument(
        "--repository-root",
        default=None,
        help="repository root; defaults to the checkout containing backend/evaluation",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "evaluate":
        return 2
    repository_root = (
        Path(args.repository_root).resolve()
        if args.repository_root
        else Path(__file__).resolve().parents[2]
    )
    try:
        run = run_evaluation(
            repository_root=repository_root,
            dataset=args.dataset,
            output_dir=Path(args.output_dir).resolve(),
        )
    except (EvaluationArtifactError, OSError, TypeError, ValueError) as error:
        print(f"evaluation failure: {error}", file=sys.stderr)
        return 2
    print(f"metrics: {run.report_path}")
    print(f"summary: {run.summary_path}")
    print(f"runtime result: {run.runtime_result_path}")
    return 0 if run.applicable_gates_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

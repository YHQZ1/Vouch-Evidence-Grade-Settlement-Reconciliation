"""Small non-interactive runtime CLI for deterministic reconciliation."""

from __future__ import annotations

import argparse
import json
import sys

from app.application.reconciliation import reconciliation_service
from app.infrastructure.ingestion import FatalSourceError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    reconcile = subparsers.add_parser("reconcile")
    reconcile.add_argument("--gateway", required=True)
    reconcile.add_argument("--bank", required=True)
    reconcile.add_argument("--ledger", required=True)
    reconcile.add_argument("--policy", required=True)
    reconcile.add_argument("--evaluation-clock", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "reconcile":
        return 2
    try:
        result = reconciliation_service.reconcile(
            gateway_path=args.gateway,
            bank_path=args.bank,
            ledger_path=args.ledger,
            policy_path=args.policy,
            evaluation_clock=args.evaluation_clock,
        )
    except (FatalSourceError, OSError, TypeError, ValueError) as error:
        print(f"reconciliation input failure: {error}", file=sys.stderr)
        return 2
    payload = result.model_dump(mode="json")
    print(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

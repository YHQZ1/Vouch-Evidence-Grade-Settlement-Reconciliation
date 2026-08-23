"""Deterministic UTF-8/LF writers and file fingerprint helpers."""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from synthetic_data.generator import (
    BANK_COLUMNS,
    GATEWAY_COLUMNS,
    LEDGER_COLUMNS,
    GeneratedDesign,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(
    path: Path, columns: tuple[str, ...], rows: Iterable[dict[str, str | None]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(columns),
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) or "" for column in columns})


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        separators=(",", ": "),
    )
    path.write_text(f"{encoded}\n", encoding="utf-8", newline="\n")


def write_runtime_inputs(design: GeneratedDesign, inputs_dir: Path) -> dict[str, Path]:
    """Write only runtime-consumable files and return their paths."""

    inputs_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "razorpay_recon.csv": inputs_dir / "razorpay_recon.csv",
        "bank_statement.csv": inputs_dir / "bank_statement.csv",
        "general_ledger.csv": inputs_dir / "general_ledger.csv",
        "batch_policy.json": inputs_dir / "batch_policy.json",
    }
    write_csv(paths["razorpay_recon.csv"], GATEWAY_COLUMNS, design.gateway_rows)
    write_csv(paths["bank_statement.csv"], BANK_COLUMNS, design.bank_rows)
    write_csv(paths["general_ledger.csv"], LEDGER_COLUMNS, design.ledger_rows)
    write_json(paths["batch_policy.json"], design.policy)
    return paths


def runtime_manifest(
    design: GeneratedDesign,
    paths: dict[str, Path],
    *,
    generation_command: str,
) -> dict[str, Any]:
    counts = {
        "razorpay_recon": len(design.gateway_rows),
        "bank_statement": len(design.bank_rows),
        "general_ledger": len(design.ledger_rows),
    }
    files = {
        filename: {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for filename, path in sorted(paths.items())
    }
    return {
        "dataset_id": design.dataset_id,
        "dataset_kind": design.dataset_kind,
        "generator_version": design.generator_version,
        "schema_version": "v1",
        "seed": design.seed,
        "fixed_evaluation_clock": design.fixed_clock,
        "source_filenames": sorted(paths),
        "files": files,
        "record_counts": counts,
        "settlement_count": len(design.settlements),
        "generation_command": generation_command,
    }


__all__ = [
    "runtime_manifest",
    "sha256_file",
    "write_csv",
    "write_json",
    "write_runtime_inputs",
]

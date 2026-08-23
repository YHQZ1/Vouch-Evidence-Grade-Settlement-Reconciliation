"""Non-interactive command line interface for Phase 3 artifacts."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from synthetic_data.generator import dataset_seed, generate_design
from synthetic_data.ground_truth import build_ground_truth
from synthetic_data.verification import verify_dataset
from synthetic_data.writers import (
    runtime_manifest,
    sha256_file,
    write_json,
    write_runtime_inputs,
)

DATASET_KINDS = ("development", "demonstration", "held_out")


def canonical_dataset_kind(value: str) -> str:
    normalized = value.replace("-", "_")
    if normalized not in DATASET_KINDS:
        raise ValueError(f"dataset must be one of {', '.join(DATASET_KINDS)}")
    return normalized


def repository_data_root() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


def _artifact_paths(data_root: Path, dataset_kind: str) -> list[Path]:
    return [
        data_root / dataset_kind / "inputs" / filename
        for filename in (
            "razorpay_recon.csv",
            "bank_statement.csv",
            "general_ledger.csv",
            "batch_policy.json",
        )
    ] + [
        data_root / "manifests" / f"{dataset_kind}.json",
        data_root / "ground_truth" / dataset_kind / "ground_truth.json",
        data_root / "ground_truth" / dataset_kind / "manifest.json",
    ]


def generate_dataset(
    dataset_kind: str,
    *,
    data_root: Path | None = None,
    seed: int | None = None,
    overwrite: bool = False,
) -> dict[str, object]:
    dataset_kind = canonical_dataset_kind(dataset_kind)
    root = data_root or repository_data_root()
    paths = _artifact_paths(root, dataset_kind)
    existing = [path for path in paths if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "frozen artifacts already exist; pass --overwrite explicitly: "
            + ", ".join(str(path) for path in existing)
        )
    design = generate_design(dataset_kind, seed=seed)
    input_paths = write_runtime_inputs(design, root / dataset_kind / "inputs")
    effective_seed = dataset_seed(dataset_kind) if seed is None else seed
    public_dataset = dataset_kind.replace("_", "-")
    generation_command = (
        "python -m synthetic_data generate "
        f"--dataset {public_dataset} --seed {effective_seed}"
    )
    manifest = runtime_manifest(
        design, input_paths, generation_command=generation_command
    )
    manifest_path = root / "manifests" / f"{dataset_kind}.json"
    write_json(manifest_path, manifest)
    ground_truth = build_ground_truth(design, input_paths, manifest)
    ground_truth_path = root / "ground_truth" / dataset_kind / "ground_truth.json"
    write_json(ground_truth_path, ground_truth)
    ground_truth_manifest = {
        "ground_truth_schema_version": ground_truth["ground_truth_schema_version"],
        "dataset_id": design.dataset_id,
        "dataset_kind": design.dataset_kind,
        "generator_version": design.generator_version,
        "seed": design.seed,
        "fixed_evaluation_clock": design.fixed_clock,
        "source_fingerprints": ground_truth["source_fingerprints"],
        "ground_truth_artifact": {
            "filename": ground_truth_path.name,
            "sha256": sha256_file(ground_truth_path),
            "bytes": ground_truth_path.stat().st_size,
        },
    }
    write_json(
        root / "ground_truth" / dataset_kind / "manifest.json",
        ground_truth_manifest,
    )
    return {
        "dataset_kind": dataset_kind,
        "manifest": manifest_path,
        "ground_truth": ground_truth_path,
        "counts": manifest["record_counts"],
    }


def check_frozen(data_root: Path | None = None) -> list[str]:
    root = data_root or repository_data_root()
    failures: list[str] = []
    for dataset_kind in DATASET_KINDS:
        with tempfile.TemporaryDirectory(prefix=f"vouch-{dataset_kind}-") as temp:
            temp_root = Path(temp) / "data"
            generate_dataset(dataset_kind, data_root=temp_root)
            expected_paths = _artifact_paths(root, dataset_kind)
            actual_paths = _artifact_paths(temp_root, dataset_kind)
            for expected, actual in zip(expected_paths, actual_paths, strict=True):
                if (
                    not expected.exists()
                    or expected.read_bytes() != actual.read_bytes()
                ):
                    failures.append(str(expected))
    return failures


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m synthetic_data")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="write one frozen dataset")
    generate.add_argument(
        "--dataset", choices=(*DATASET_KINDS, "held-out"), required=True
    )
    generate.add_argument("--seed", type=int)
    generate.add_argument("--data-root", type=Path)
    generate.add_argument("--overwrite", action="store_true")
    verify = subparsers.add_parser("verify", help="verify emitted artifacts read-only")
    verify.add_argument("--dataset", choices=(*DATASET_KINDS, "held-out"))
    verify.add_argument("--all", action="store_true")
    verify.add_argument("--data-root", type=Path)
    verify_all = subparsers.add_parser("verify-all", help="verify all emitted datasets")
    verify_all.add_argument("--data-root", type=Path)
    frozen = subparsers.add_parser(
        "check-frozen", help="regenerate and compare frozen bytes"
    )
    frozen.add_argument("--data-root", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "generate":
            result = generate_dataset(
                args.dataset,
                data_root=args.data_root,
                seed=args.seed,
                overwrite=args.overwrite,
            )
            print(f"generated {result['dataset_kind']}: {result['counts']}")
            return 0
        if args.command == "verify":
            if args.all:
                for dataset_kind in DATASET_KINDS:
                    result = verify_dataset(dataset_kind, data_root=args.data_root)
                    print(f"verified {dataset_kind}: {result['record_counts']}")
                return 0
            if args.dataset is None:
                raise ValueError("verify requires --dataset or --all")
            result = verify_dataset(args.dataset, data_root=args.data_root)
            print(f"verified {args.dataset}: {result['record_counts']}")
            return 0
        if args.command == "verify-all":
            for dataset_kind in DATASET_KINDS:
                result = verify_dataset(dataset_kind, data_root=args.data_root)
                print(f"verified {dataset_kind}: {result['record_counts']}")
            return 0
        failures = check_frozen(args.data_root)
        if failures:
            print("frozen artifact mismatch:", file=sys.stderr)
            print("\n".join(failures), file=sys.stderr)
            return 1
        print("frozen artifacts are byte-for-byte reproducible")
        return 0
    except Exception as error:  # CLI must turn invariant failures into exit 1.
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

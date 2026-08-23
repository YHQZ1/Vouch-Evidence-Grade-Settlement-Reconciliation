"""Evaluation-only adapters for manifests, runtime results, and labels."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.domain import BatchResult
from evaluation.contracts import (
    GroundTruthManifest,
    LabelAdapterOutput,
    RuntimeManifest,
)

EXPECTED_RULE_VERSION = "phase4-deterministic-v1"


class EvaluationArtifactError(ValueError):
    """Raised when an evaluation input is malformed, stale, or tampered."""


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON with the repository-wide deterministic wire format."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvaluationArtifactError(
            f"cannot read JSON artifact {path}: {error}"
        ) from error


def _sha256(path: Path) -> tuple[int, str]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise EvaluationArtifactError(
            f"cannot read artifact {path}: {error}"
        ) from error
    return len(payload), hashlib.sha256(payload).hexdigest()


def dataset_key(dataset: str) -> str:
    key = dataset.strip().lower().replace("-", "_")
    if key not in {"development", "demonstration", "held_out"}:
        raise EvaluationArtifactError(f"unsupported dataset: {dataset}")
    return key


def load_runtime_manifest(repository_root: Path, dataset: str) -> RuntimeManifest:
    key = dataset_key(dataset)
    path = repository_root / "data" / "manifests" / f"{key}.json"
    try:
        manifest = RuntimeManifest.model_validate(_read_json(path))
    except Exception as error:
        if isinstance(error, EvaluationArtifactError):
            raise
        raise EvaluationArtifactError(
            f"invalid runtime manifest {path}: {error}"
        ) from error

    input_root = repository_root / "data" / key / "inputs"
    if manifest.dataset_kind != key or manifest.dataset_id != f"vouch-phase3-{key}":
        raise EvaluationArtifactError(
            "runtime manifest dataset identity is inconsistent"
        )
    if tuple(sorted(manifest.files)) != tuple(sorted(manifest.source_filenames)):
        raise EvaluationArtifactError("runtime manifest file inventory is inconsistent")
    for filename, expected in manifest.files.items():
        source = input_root / filename
        byte_count, fingerprint = _sha256(source)
        if (byte_count, fingerprint) != (expected.bytes, expected.sha256):
            raise EvaluationArtifactError(
                f"runtime input fingerprint mismatch: {filename}"
            )
    return manifest


def load_runtime_result(
    path: Path, *, expected: BatchResult | None = None
) -> BatchResult:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise EvaluationArtifactError("runtime-result.json must contain a JSON object")
    _assert_no_label_only_fields(payload)
    try:
        result = BatchResult.model_validate(payload)
    except Exception as error:
        raise EvaluationArtifactError(f"invalid runtime result: {error}") from error
    canonical = canonical_json_bytes(result.model_dump(mode="json"))
    try:
        actual = path.read_bytes()
    except OSError as error:
        raise EvaluationArtifactError(
            f"cannot read runtime result {path}: {error}"
        ) from error
    if actual != canonical:
        raise EvaluationArtifactError(
            "runtime-result.json is not the canonical result emitted by the engine"
        )
    if expected is not None and result != expected:
        raise EvaluationArtifactError(
            "runtime-result.json does not match the deterministic engine result"
        )
    return result


def save_runtime_result(path: Path, result: BatchResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(result.model_dump(mode="json")))


def validate_runtime_result_identity(
    result: BatchResult, manifest: RuntimeManifest
) -> None:
    """Reject a valid-looking result that belongs to another runtime batch."""

    if result.schema_version != manifest.schema_version:
        raise EvaluationArtifactError("runtime result schema version mismatch")
    if result.rule_version != EXPECTED_RULE_VERSION:
        raise EvaluationArtifactError("runtime result rule version is not supported")
    if (
        result.evaluation_clock.isoformat().replace("+00:00", "Z")
        != manifest.fixed_evaluation_clock
    ):
        raise EvaluationArtifactError("runtime result fixed clock mismatch")
    fingerprints = {
        item.source_name: item.sha256 for item in result.source_fingerprints
    }
    expected_fingerprints = {name: item.sha256 for name, item in manifest.files.items()}
    if fingerprints != expected_fingerprints:
        raise EvaluationArtifactError("runtime result source fingerprints mismatch")
    if len(result.settlements) != manifest.settlement_count:
        raise EvaluationArtifactError("runtime result settlement count mismatch")
    for summary in result.ingestion:
        expected_count = manifest.record_counts.get(
            summary.source_name.removesuffix(".csv")
        )
        if expected_count is not None and summary.row_count != expected_count:
            raise EvaluationArtifactError(
                f"runtime result row count mismatch: {summary.source_name}"
            )


def load_ground_truth(
    repository_root: Path,
    dataset: str,
    runtime_manifest: RuntimeManifest,
) -> LabelAdapterOutput:
    """Load labels only after the caller has persisted the runtime result."""

    key = dataset_key(dataset)
    directory = repository_root / "data" / "ground_truth" / key
    manifest_path = directory / "manifest.json"
    try:
        manifest = GroundTruthManifest.model_validate(_read_json(manifest_path))
    except Exception as error:
        if isinstance(error, EvaluationArtifactError):
            raise
        raise EvaluationArtifactError(
            f"invalid ground-truth manifest {manifest_path}: {error}"
        ) from error

    if (
        manifest.dataset_id != runtime_manifest.dataset_id
        or manifest.dataset_kind != runtime_manifest.dataset_kind
        or manifest.generator_version != runtime_manifest.generator_version
        or manifest.seed != runtime_manifest.seed
        or manifest.fixed_evaluation_clock != runtime_manifest.fixed_evaluation_clock
        or manifest.source_fingerprints
        != {name: item.sha256 for name, item in runtime_manifest.files.items()}
    ):
        raise EvaluationArtifactError("runtime and ground-truth identities disagree")

    artifact_path = directory / manifest.ground_truth_artifact.filename
    byte_count, fingerprint = _sha256(artifact_path)
    if (byte_count, fingerprint) != (
        manifest.ground_truth_artifact.bytes,
        manifest.ground_truth_artifact.sha256,
    ):
        raise EvaluationArtifactError("ground-truth artifact fingerprint mismatch")
    try:
        truth = LabelAdapterOutput.model_validate(_read_json(artifact_path))
    except Exception as error:
        if isinstance(error, EvaluationArtifactError):
            raise
        raise EvaluationArtifactError(
            f"invalid ground-truth artifact: {error}"
        ) from error
    if (
        truth.dataset_id != manifest.dataset_id
        or truth.dataset_kind != manifest.dataset_kind
        or truth.generator_version != manifest.generator_version
        or truth.seed != manifest.seed
        or truth.fixed_evaluation_clock != manifest.fixed_evaluation_clock
        or truth.source_fingerprints != manifest.source_fingerprints
        or truth.ground_truth_schema_version != manifest.ground_truth_schema_version
    ):
        raise EvaluationArtifactError("ground-truth artifact and manifest disagree")
    return truth


def _assert_no_label_only_fields(value: Any) -> None:
    forbidden_markers = (
        "ground_truth",
        "groundtruth",
        "scenario_ids",
        "expected_",
        "label_only",
    )
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if any(marker in normalized for marker in forbidden_markers):
                raise EvaluationArtifactError(
                    f"runtime result contains label-only field: {key}"
                )
            _assert_no_label_only_fields(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_label_only_fields(child)


__all__ = [
    "EvaluationArtifactError",
    "canonical_json_bytes",
    "dataset_key",
    "load_ground_truth",
    "load_runtime_manifest",
    "load_runtime_result",
    "save_runtime_result",
    "validate_runtime_result_identity",
]

"""Independent, disk-based checks for Phase 3 artifacts."""

from __future__ import annotations

import ast
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.domain import BankEntry, GatewayMovement, LedgerLine, SourceKind, SourceLineage
from synthetic_data import GENERATOR_VERSION
from synthetic_data.generator import BANK_COLUMNS, GATEWAY_COLUMNS, LEDGER_COLUMNS
from synthetic_data.scenarios import REQUIRED_SCENARIO_IDS, SCENARIO_BY_ID
from synthetic_data.writers import sha256_file

DATASET_KINDS = ("development", "demonstration", "held_out")


def repository_data_root() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


class VerificationError(ValueError):
    """Raised when an emitted dataset violates a Phase 3 invariant."""


MONEY_COLUMNS = {
    "debit",
    "credit",
    "amount",
    "fee",
    "tax",
    "balance_after",
}
INTEGER_RE = re.compile(r"^(0|[1-9][0-9]*)$")
FORBIDDEN_RUNTIME_TOKENS = (
    "ground_truth",
    "ground-truth",
    "scenario_id",
    "expected_resolution",
    "auto_clear_eligibility",
    "blocking_behavior",
    "answer_key",
)


def _paths(
    data_root: Path, dataset_kind: str
) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
    input_dir = data_root / dataset_kind / "inputs"
    return (
        input_dir / "razorpay_recon.csv",
        input_dir / "bank_statement.csv",
        input_dir / "general_ledger.csv",
        input_dir / "batch_policy.json",
        data_root / "manifests" / f"{dataset_kind}.json",
        data_root / "ground_truth" / dataset_kind / "ground_truth.json",
        data_root / "ground_truth" / dataset_kind / "manifest.json",
    )


def _read_utf8_lf(path: Path) -> str:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise VerificationError(f"{path} is not UTF-8") from error
    if "\r" in text:
        raise VerificationError(f"{path} contains CR line endings")
    if not text.endswith("\n"):
        raise VerificationError(f"{path} must end with LF")
    return text


def _read_csv(path: Path, expected_columns: tuple[str, ...]) -> list[dict[str, str]]:
    text = _read_utf8_lf(path)
    rows = list(csv.DictReader(text.splitlines()))
    if not rows and text.strip() == "":
        raise VerificationError(f"{path} is empty")
    reader = csv.DictReader(text.splitlines())
    if tuple(reader.fieldnames or ()) != expected_columns:
        raise VerificationError(f"{path.name} columns do not match the contract")
    # DictReader has already consumed the split text; construct the rows once
    # more through the same deterministic input, retaining strings at the file boundary.
    return rows


def _integer(
    value: str, *, field: str, path: Path, row_number: int, allow_empty: bool = False
) -> int | None:
    if allow_empty and value == "":
        return None
    if not INTEGER_RE.fullmatch(value):
        raise VerificationError(
            f"{path.name}:{row_number} {field} is not integer paise"
        )
    return int(value)


def _optional(row: dict[str, str], key: str) -> str | None:
    value = row.get(key, "")
    return value if value != "" else None


def _bool(value: str, *, field: str, path: Path, row_number: int) -> bool:
    if value not in {"true", "false"}:
        raise VerificationError(
            f"{path.name}:{row_number} {field} is not lowercase boolean"
        )
    return value == "true"


def _lineage(
    path: Path, source_kind: SourceKind, fingerprint: str, row_number: int
) -> SourceLineage:
    return SourceLineage(
        source_kind=source_kind,
        source_name=path.name,
        source_fingerprint=fingerprint,
        source_row_number=row_number,
    )


def _raw(row: dict[str, str]) -> dict[str, str | None]:
    return {key: (value if value != "" else None) for key, value in row.items()}


def _canonical_gateway(
    path: Path, fingerprint: str, row: dict[str, str], number: int
) -> GatewayMovement:
    return GatewayMovement(
        lineage=_lineage(path, SourceKind.GATEWAY, fingerprint, number),
        raw_values=_raw(row),
        entity_id=row["entity_id"],
        type=row["type"],
        debit=int(row["debit"]),
        credit=int(row["credit"]),
        amount=int(row["amount"]),
        currency=row["currency"],
        fee=int(row["fee"]),
        tax=int(row["tax"]),
        on_hold=_bool(row["on_hold"], field="on_hold", path=path, row_number=number),
        settled=_bool(row["settled"], field="settled", path=path, row_number=number),
        created_at=row["created_at"],
        settled_at=_optional(row, "settled_at"),
        settlement_id=_optional(row, "settlement_id"),
        description=_optional(row, "description"),
        notes=_optional(row, "notes"),
        payment_id=_optional(row, "payment_id"),
        settlement_utr=_optional(row, "settlement_utr"),
        order_id=_optional(row, "order_id"),
        order_receipt=_optional(row, "order_receipt"),
        method=_optional(row, "method"),
        card_network=_optional(row, "card_network"),
        card_issuer=_optional(row, "card_issuer"),
        card_type=_optional(row, "card_type"),
        dispute_id=_optional(row, "dispute_id"),
        channel_type=_optional(row, "channel_type"),
        balance_account_id=_optional(row, "balance_account_id"),
    )


def _canonical_bank(
    path: Path, fingerprint: str, row: dict[str, str], number: int
) -> BankEntry:
    return BankEntry(
        lineage=_lineage(path, SourceKind.BANK, fingerprint, number),
        raw_values=_raw(row),
        bank_row_id=row["bank_row_id"],
        posted_at=row["posted_at"],
        direction=row["direction"],
        amount=int(row["amount"]),
        currency=row["currency"],
        narration=row["narration"],
        value_date=_optional(row, "value_date"),
        reference=_optional(row, "reference"),
        account_suffix=_optional(row, "account_suffix"),
        balance_after=int(row["balance_after"]) if row["balance_after"] else None,
        normalized_utr=_optional(row, "reference"),
    )


def _canonical_ledger(
    path: Path, fingerprint: str, row: dict[str, str], number: int
) -> LedgerLine:
    return LedgerLine(
        lineage=_lineage(path, SourceKind.LEDGER, fingerprint, number),
        raw_values=_raw(row),
        journal_id=row["journal_id"],
        line_id=row["line_id"],
        posted_at=row["posted_at"],
        account_code=row["account_code"],
        account_name=row["account_name"],
        debit=int(row["debit"]),
        credit=int(row["credit"]),
        currency=row["currency"],
        reference=_optional(row, "reference"),
        narration=_optional(row, "narration"),
        order_id=_optional(row, "order_id"),
        payment_id=_optional(row, "payment_id"),
        settlement_id=_optional(row, "settlement_id"),
        utr=_optional(row, "utr"),
        voucher_type=_optional(row, "voucher_type"),
    )


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _sla_hours(policy: dict[str, Any]) -> int:
    return int(policy["settlement_sla"][0]["max_age_hours"])


def _materiality_is_blocking(
    value_subunits: int, policy: dict[str, Any], batch_total_abs_subunits: int
) -> bool:
    """Independent verifier oracle for the frozen absolute/relative policy."""

    value = abs(value_subunits)
    absolute_threshold = int(policy["materiality_absolute_subunits"])
    relative_bps = policy.get("materiality_relative_bps")
    relative_triggered = (
        relative_bps is not None
        and value * 10_000 >= batch_total_abs_subunits * int(relative_bps)
    )
    return value >= absolute_threshold or relative_triggered


def _verify_scenario_evidence(
    *,
    dataset_kind: str,
    gateway: list[GatewayMovement],
    bank: list[BankEntry],
    ledger: list[LedgerLine],
    gateway_errors: dict[int, str],
    ground_truth: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    """Prove labels against emitted rows, independently of generator state."""

    settlements = ground_truth["settlements"]
    by_settlement: defaultdict[str, list[GatewayMovement]] = defaultdict(list)
    for row in gateway:
        if row.settlement_id:
            by_settlement[row.settlement_id].append(row)
    by_ledger_settlement: defaultdict[str, list[LedgerLine]] = defaultdict(list)
    for row in ledger:
        if row.settlement_id:
            by_ledger_settlement[row.settlement_id].append(row)
    evaluation_clock = _timestamp(ground_truth["fixed_evaluation_clock"])
    sla = timedelta(hours=_sla_hours(policy))

    def fail(scenario_id: str, settlement_id: str, message: str) -> None:
        raise VerificationError(
            f"{scenario_id} evidence for {settlement_id}: {message}"
        )

    claimed_ids: set[str] = set()
    for label in settlements:
        settlement_id = label["settlement_id"]
        scenario_ids = label["scenario_ids"]
        claimed_ids.update(scenario_ids)
        rows = by_settlement[settlement_id]
        journals = by_ledger_settlement[settlement_id]
        payments = [row for row in rows if row.type == "payment"]
        refunds = [row for row in rows if row.type == "refund"]
        if "clean_multi_payment_settlement" in scenario_ids and len(payments) < 2:
            fail(
                "clean_multi_payment_settlement",
                settlement_id,
                "fewer than two payments",
            )
        fee_rows = [row for row in rows if row.fee > 0]
        tax_rows = [row for row in rows if row.tax > 0]
        if "normal_fees_and_tax" in scenario_ids:
            if not fee_rows or not tax_rows:
                fail("normal_fees_and_tax", settlement_id, "fee or tax movement absent")
            fee_amounts = {row.fee for row in fee_rows}
            tax_amounts = {row.tax for row in tax_rows}
            if not any(
                line.account_code == "5100" and line.debit in fee_amounts
                for line in journals
            ):
                if "incorrect_fee_booking" not in scenario_ids:
                    fail(
                        "normal_fees_and_tax",
                        settlement_id,
                        "fee is not posted to fee role",
                    )
            if not any(
                line.account_code == "2100" and line.debit in tax_amounts
                for line in journals
            ):
                if "incorrect_tax_booking" not in scenario_ids:
                    fail(
                        "normal_fees_and_tax",
                        settlement_id,
                        "tax is not posted to tax role",
                    )
        if "incorrect_fee_booking" in scenario_ids:
            if not fee_rows or not any(
                line.account_code == "6000"
                and line.debit in {row.fee for row in fee_rows}
                for line in journals
            ):
                fail(
                    "incorrect_fee_booking",
                    settlement_id,
                    "wrong-role fee posting absent",
                )
        if "incorrect_tax_booking" in scenario_ids:
            if not tax_rows or not any(
                line.account_code == "6000"
                and line.debit in {row.tax for row in tax_rows}
                for line in journals
            ):
                fail(
                    "incorrect_tax_booking",
                    settlement_id,
                    "wrong-role tax posting absent",
                )
        if "same_settlement_refund" in scenario_ids:
            payment_ids = {row.entity_id for row in payments}
            if not refunds or not any(row.payment_id in payment_ids for row in refunds):
                fail(
                    "same_settlement_refund",
                    settlement_id,
                    "same-settlement refund absent",
                )
        if "later_settlement_refund" in scenario_ids:
            payment_ids = {row.entity_id for row in payments}
            all_payments = {
                row.entity_id: row for row in gateway if row.type == "payment"
            }
            if not refunds or not any(
                row.payment_id not in payment_ids
                and row.payment_id in all_payments
                and row.settled_at is not None
                and all_payments[row.payment_id].settled_at is not None
                and row.settled_at > all_payments[row.payment_id].settled_at
                for row in refunds
            ):
                fail(
                    "later_settlement_refund",
                    settlement_id,
                    "later refund relationship absent",
                )
        if "transfer_movement" in scenario_ids and not any(
            row.type == "transfer" for row in rows
        ):
            fail("transfer_movement", settlement_id, "transfer movement absent")
        if "adjustment_movement" in scenario_ids and not any(
            row.type == "adjustment" and row.fee == 0 and row.tax == 0 for row in rows
        ):
            fail(
                "adjustment_movement", settlement_id, "plain adjustment movement absent"
            )
        if "missing_settlement_utr" in scenario_ids and any(
            row.settlement_utr for row in rows
        ):
            fail(
                "missing_settlement_utr",
                settlement_id,
                "gateway UTR unexpectedly present",
            )
        target_net = sum(row.signed_net.subunits for row in rows)
        target_banks = [
            row for row in bank if row.is_credit and row.amount == target_net
        ]
        gateway_utrs = {row.settlement_utr for row in rows if row.settlement_utr}
        if "corrupted_conflicting_utr" in scenario_ids:
            if not gateway_utrs or not any(
                row.account_suffix == label["balance_account_id"]
                and row.normalized_utr not in gateway_utrs
                for row in target_banks
            ):
                fail(
                    "corrupted_conflicting_utr",
                    settlement_id,
                    "conflicting bank reference absent",
                )
        if "valid_bank_arrival_within_sla" in scenario_ids:
            exact = [
                row
                for row in target_banks
                if row.account_suffix == label["balance_account_id"]
                and row.normalized_utr in gateway_utrs
            ]
            latest = max(row.settled_at for row in rows if row.settled_at)
            if not exact or any(
                not (latest < row.posted_at <= latest + sla) for row in exact
            ):
                fail(
                    "valid_bank_arrival_within_sla",
                    settlement_id,
                    "exact arrival is outside SLA",
                )
            if label["expected_resolution_state"] != "auto_cleared":
                fail(
                    "valid_bank_arrival_within_sla",
                    settlement_id,
                    "arrival is not expected cleared",
                )
        if "pending_within_sla" in scenario_ids:
            latest = max(row.settled_at for row in rows if row.settled_at)
            if any(row.normalized_utr in gateway_utrs for row in bank if row.is_credit):
                fail(
                    "pending_within_sla",
                    settlement_id,
                    "bank credit unexpectedly present",
                )
            if not latest < evaluation_clock < latest + sla:
                fail(
                    "pending_within_sla",
                    settlement_id,
                    "elapsed time is not within SLA",
                )
            if label["expected_resolution_state"] != "pending_within_sla":
                fail("pending_within_sla", settlement_id, "state is not pending")
        if "overdue_missing_bank_credit" in scenario_ids:
            latest = max(row.settled_at for row in rows if row.settled_at)
            if any(row.normalized_utr in gateway_utrs for row in bank if row.is_credit):
                fail(
                    "overdue_missing_bank_credit",
                    settlement_id,
                    "bank credit unexpectedly present",
                )
            if evaluation_clock <= latest + sla:
                fail(
                    "overdue_missing_bank_credit",
                    settlement_id,
                    "elapsed time is not overdue",
                )
        if "duplicate_ledger_line" in scenario_ids:
            counts = Counter(row.line_id for row in journals)
            if not any(count > 1 for count in counts.values()):
                fail("duplicate_ledger_line", settlement_id, "duplicate line absent")
        if "missing_ledger_line" in scenario_ids:
            journal_counts = Counter(row.journal_id for row in journals)
            if not any(count < 2 for count in journal_counts.values()):
                fail(
                    "missing_ledger_line", settlement_id, "missing journal line absent"
                )
        if "amount_date_collision" in scenario_ids:
            candidates = [
                row
                for row in target_banks
                if row.account_suffix == label["balance_account_id"]
            ]
            if (
                len({(row.amount, row.posted_at) for row in candidates}) != 1
                or len(candidates) < 2
            ):
                fail(
                    "amount_date_collision",
                    settlement_id,
                    "same amount/date candidates absent",
                )
        if "balance_account_isolation" in scenario_ids:
            exact = [row for row in target_banks if row.normalized_utr in gateway_utrs]
            if not exact or not any(
                row.amount == exact[0].amount
                and row.normalized_utr == exact[0].normalized_utr
                and row.account_suffix != label["balance_account_id"]
                for row in bank
            ):
                fail(
                    "balance_account_isolation",
                    settlement_id,
                    "wrong-account proof adversary absent",
                )
            if (
                label["expected_resolution_state"]
                not in {
                    "auto_cleared",
                    "cleared_with_explanation",
                }
                or "balance_account_conflict" in label["expected_reason_codes"]
            ):
                fail(
                    "balance_account_isolation",
                    settlement_id,
                    "partitioned candidate incorrectly changed the valid outcome",
                )
        if "amount_resemblance_is_not_label" in scenario_ids:
            exact = [row for row in target_banks if row.normalized_utr in gateway_utrs]
            if not exact or not any(
                row.amount == exact[0].amount
                and row.posted_at == exact[0].posted_at
                and row.normalized_utr is None
                for row in bank
            ):
                fail(
                    "amount_resemblance_is_not_label",
                    settlement_id,
                    "amount-only adversary absent",
                )

    global_checks = {
        "unrelated_bank_distractors": sum(
            row.bank_row_id.startswith("bank_") and "distractor_" in row.bank_row_id
            for row in bank
        )
        >= 3,
        "malformed_source_rows": bool(gateway_errors),
        "untrusted_instruction_narration": any(
            "ignore all previous instructions" in row.narration.casefold()
            for row in bank
        ),
    }
    for scenario_id, present in global_checks.items():
        if scenario_id in ground_truth["required_scenarios_present"] and not present:
            fail(scenario_id, "batch", "declared evidence is absent")
        if scenario_id in ground_truth["required_scenarios_present"]:
            claimed_ids.add(scenario_id)
    if not set(ground_truth["required_scenarios_present"]).issubset(SCENARIO_BY_ID):
        raise VerificationError("ground truth contains an unknown scenario ID")
    if dataset_kind != "development":
        missing = REQUIRED_SCENARIO_IDS - claimed_ids
        if missing:
            raise VerificationError(
                f"required scenario evidence is absent: {sorted(missing)}"
            )


def _check_runtime_import_boundary() -> None:
    app_root = Path(__file__).resolve().parents[1] / "app"
    violations: list[str] = []
    forbidden = ("synthetic_data", "ground_truth", "ground-truth", "evaluation")
    for source_path in sorted(app_root.rglob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            violations.extend(
                f"{source_path.relative_to(app_root)} imports {name}"
                for name in names
                if name.startswith(forbidden)
            )
    if violations:
        raise VerificationError(
            "runtime import boundary violated: " + "; ".join(violations)
        )


def verify_dataset(
    dataset_kind: str, *, data_root: Path | None = None
) -> dict[str, Any]:
    dataset_kind = dataset_kind.replace("-", "_")
    if dataset_kind not in DATASET_KINDS:
        raise VerificationError(f"unsupported dataset: {dataset_kind}")
    root = data_root or repository_data_root()
    (
        gateway_path,
        bank_path,
        ledger_path,
        policy_path,
        manifest_path,
        truth_path,
        truth_manifest_path,
    ) = _paths(root, dataset_kind)
    for path in (
        gateway_path,
        bank_path,
        ledger_path,
        policy_path,
        manifest_path,
        truth_path,
        truth_manifest_path,
    ):
        if not path.exists():
            raise VerificationError(f"missing required artifact: {path}")
    manifest = json.loads(_read_utf8_lf(manifest_path))
    ground_truth = json.loads(_read_utf8_lf(truth_path))
    truth_manifest = json.loads(_read_utf8_lf(truth_manifest_path))
    if manifest.get("generator_version") != GENERATOR_VERSION:
        raise VerificationError("manifest generator version mismatch")
    if ground_truth.get("generator_version") != GENERATOR_VERSION:
        raise VerificationError("ground-truth generator version mismatch")
    if truth_manifest.get("generator_version") != GENERATOR_VERSION:
        raise VerificationError("ground-truth manifest generator version mismatch")

    runtime_text = "\n".join(
        _read_utf8_lf(path)
        for path in (gateway_path, bank_path, ledger_path, policy_path)
    )
    if any(token in runtime_text for token in FORBIDDEN_RUNTIME_TOKENS):
        raise VerificationError("ground-truth-only field leaked into runtime artifacts")
    for scenario_id in ground_truth.get("required_scenarios_present", []):
        if scenario_id in runtime_text:
            raise VerificationError(
                f"scenario label leaked into runtime artifacts: {scenario_id}"
            )

    files = {
        gateway_path.name: gateway_path,
        bank_path.name: bank_path,
        ledger_path.name: ledger_path,
        policy_path.name: policy_path,
    }
    for filename, path in files.items():
        actual_hash = sha256_file(path)
        if manifest["files"][filename]["sha256"] != actual_hash:
            raise VerificationError(f"manifest hash mismatch for {filename}")
        if manifest["files"][filename]["bytes"] != path.stat().st_size:
            raise VerificationError(f"manifest byte count mismatch for {filename}")
        if ground_truth["source_fingerprints"][filename] != actual_hash:
            raise VerificationError(f"ground-truth fingerprint mismatch for {filename}")
    truth_file = truth_manifest.get("ground_truth_artifact", {})
    if truth_file.get("sha256") != sha256_file(truth_path):
        raise VerificationError("ground-truth manifest hash mismatch")
    if truth_file.get("bytes") != truth_path.stat().st_size:
        raise VerificationError("ground-truth manifest byte count mismatch")
    policy = json.loads(_read_utf8_lf(policy_path))

    gateway_rows = _read_csv(gateway_path, GATEWAY_COLUMNS)
    bank_rows = _read_csv(bank_path, BANK_COLUMNS)
    ledger_rows = _read_csv(ledger_path, LEDGER_COLUMNS)
    for path, rows in (
        (gateway_path, gateway_rows),
        (bank_path, bank_rows),
        (ledger_path, ledger_rows),
    ):
        for number, row in enumerate(rows, start=1):
            for field, value in row.items():
                if field in MONEY_COLUMNS and value != "":
                    _integer(value, field=field, path=path, row_number=number)
            if any(
                value.lower() in {"nan", "inf", "-inf", "infinity", "-infinity"}
                for value in row.values()
            ):
                raise VerificationError(f"non-finite value in {path.name}:{number}")

    gateway_fingerprint = sha256_file(gateway_path)
    bank_fingerprint = sha256_file(bank_path)
    ledger_fingerprint = sha256_file(ledger_path)
    valid_gateway: list[GatewayMovement] = []
    gateway_errors: dict[int, str] = {}
    for number, row in enumerate(gateway_rows, start=1):
        try:
            valid_gateway.append(
                _canonical_gateway(gateway_path, gateway_fingerprint, row, number)
            )
        except (ValidationError, TypeError, ValueError) as error:
            gateway_errors[number] = str(error)
    valid_bank: list[BankEntry] = []
    bank_errors: dict[int, str] = {}
    for number, row in enumerate(bank_rows, start=1):
        try:
            valid_bank.append(_canonical_bank(bank_path, bank_fingerprint, row, number))
        except (ValidationError, TypeError, ValueError) as error:
            bank_errors[number] = str(error)
    valid_ledger: list[LedgerLine] = []
    ledger_errors: dict[int, str] = {}
    for number, row in enumerate(ledger_rows, start=1):
        try:
            valid_ledger.append(
                _canonical_ledger(ledger_path, ledger_fingerprint, row, number)
            )
        except (ValidationError, TypeError, ValueError) as error:
            ledger_errors[number] = str(error)
    if bank_errors or ledger_errors:
        raise VerificationError("unexpected malformed bank or ledger rows")

    rejected = ground_truth["expected_rejected_rows"]
    rejected_numbers = {item["source_row_number"] for item in rejected}
    if set(gateway_errors) != rejected_numbers:
        raise VerificationError(f"malformed gateway rows differ: {gateway_errors}")
    if rejected and not all(
        "entity_id" in gateway_errors[number] for number in rejected_numbers
    ):
        raise VerificationError(
            "malformed rows did not fail for their expected identity reason"
        )
    if len(valid_gateway) + len(gateway_errors) != len(gateway_rows):
        raise VerificationError("gateway row accounting is incomplete")

    gateway_ids = {record.entity_id for record in valid_gateway}
    bank_ids = {record.bank_row_id for record in valid_bank}
    if len(gateway_ids) != len(valid_gateway) or len(bank_ids) != len(valid_bank):
        raise VerificationError("gateway or bank business identifiers are not unique")
    expected_duplicate_ids = {
        item["line_id"] for item in ground_truth["expected_duplicate_ledger_lines"]
    }
    counts = Counter(record.line_id for record in valid_ledger)
    duplicate_ids = {line_id for line_id, count in counts.items() if count > 1}
    if duplicate_ids != expected_duplicate_ids:
        raise VerificationError(
            "ledger duplicate identity set differs from ground truth"
        )

    settlements = ground_truth["settlements"]
    gateway_by_settlement: defaultdict[str, list[GatewayMovement]] = defaultdict(list)
    for record in valid_gateway:
        if record.settlement_id:
            gateway_by_settlement[record.settlement_id].append(record)
    expected_nets = {
        item["settlement_id"]: item["expected_net_subunits"] for item in settlements
    }
    actual_nets = {
        settlement_id: sum(item.signed_net.subunits for item in records)
        for settlement_id, records in gateway_by_settlement.items()
    }
    if actual_nets != expected_nets:
        raise VerificationError(
            "settlement signed arithmetic does not match ground truth"
        )

    batch_total_abs = sum(abs(value) for value in actual_nets.values())
    for label in settlements:
        state = label["expected_resolution_state"]
        unresolved = (
            0
            if state in {"auto_cleared", "cleared_with_explanation"}
            else abs(actual_nets[label["settlement_id"]])
        )
        computed_material = _materiality_is_blocking(
            unresolved, policy, batch_total_abs
        )
        if label["expected_unresolved_value_subunits"] != unresolved:
            raise VerificationError(
                f"unresolved value mismatch for {label['settlement_id']}"
            )
        if label["materiality"]["is_material"] != computed_material:
            raise VerificationError(
                f"materiality mismatch for {label['settlement_id']}"
            )
        computed_blocking = state == "critical_exception" or (
            state == "needs_review" and computed_material
        )
        if label["expected_blocking_behavior"] == "blocking" and not computed_blocking:
            raise VerificationError(
                f"blocking label is unsupported by policy for {label['settlement_id']}"
            )
        if computed_blocking != (label["expected_close_readiness"] == "BLOCKED"):
            raise VerificationError(
                "settlement close readiness is inconsistent for "
                f"{label['settlement_id']}"
            )
    expected_batch_readiness = (
        "BLOCKED"
        if any(label["expected_close_readiness"] == "BLOCKED" for label in settlements)
        else "READY_WITH_EXCEPTIONS"
        if any(
            label["expected_resolution_state"] == "pending_within_sla"
            for label in settlements
        )
        else "READY"
    )
    if ground_truth["expected_close_readiness"] != expected_batch_readiness:
        raise VerificationError(
            "batch close readiness is inconsistent with settlements"
        )

    bank_by_id = {record.bank_row_id: record for record in valid_bank}
    bank_link_use: Counter[str] = Counter()
    for link, label in zip(
        ground_truth["expected_settlement_to_bank_links"], settlements, strict=True
    ):
        bank_ref = link["expected_bank_credit"]
        if bank_ref is None:
            continue
        if bank_ref["bank_row_id"] not in bank_by_id:
            raise VerificationError("ground-truth bank reference does not resolve")
        bank = bank_by_id[bank_ref["bank_row_id"]]
        bank_link_use[bank.bank_row_id] += 1
        if bank.direction.value != "credit":
            raise VerificationError("expected bank settlement is not a credit")
        if label["expected_resolution_state"] in {
            "auto_cleared",
            "cleared_with_explanation",
        }:
            gateway_records = gateway_by_settlement[label["settlement_id"]]
            gateway_utrs = {
                record.settlement_utr
                for record in gateway_records
                if record.settlement_utr is not None
            }
            if len(gateway_utrs) != 1 or bank.normalized_utr not in gateway_utrs:
                raise VerificationError("clean bank credit does not agree on UTR")
            if bank.amount != label["expected_net_subunits"]:
                raise VerificationError(
                    "clean bank credit does not equal signed settlement net"
                )
            latest_gateway_time = max(
                record.settled_at for record in gateway_records if record.settled_at
            )
            if (
                bank.posted_at < latest_gateway_time
                or bank.posted_at - latest_gateway_time > timedelta(hours=48)
            ):
                raise VerificationError(
                    "clean bank credit falls outside the timing window"
                )
        if bank.account_suffix != label["balance_account_id"]:
            raise VerificationError("bank link crossed balance-account partition")
    if any(count != 1 for count in bank_link_use.values()):
        raise VerificationError("one bank row was linked to multiple settlements")

    journal_totals: defaultdict[str, list[int]] = defaultdict(lambda: [0, 0])
    for line in valid_ledger:
        journal_totals[line.journal_id][0] += line.debit
        journal_totals[line.journal_id][1] += line.credit
    actual_unbalanced = sorted(
        journal_id
        for journal_id, (debit, credit) in journal_totals.items()
        if debit != credit
    )
    if actual_unbalanced != sorted(
        ground_truth["expected_deliberately_unbalanced_journals"]
    ):
        raise VerificationError("unbalanced journal set is not explicitly labelled")

    clearing_by_settlement: defaultdict[str, int] = defaultdict(int)
    for line in valid_ledger:
        if line.account_code == "1100" and line.settlement_id:
            clearing_by_settlement[line.settlement_id] += line.signed_amount.subunits
    for label in settlements:
        if label["expected_resolution_state"] in {
            "auto_cleared",
            "cleared_with_explanation",
        }:
            if clearing_by_settlement[label["settlement_id"]] != 0:
                raise VerificationError("clean clearing-account residual is non-zero")

    _verify_scenario_evidence(
        dataset_kind=dataset_kind,
        gateway=valid_gateway,
        bank=valid_bank,
        ledger=valid_ledger,
        gateway_errors=gateway_errors,
        ground_truth=ground_truth,
        policy=policy,
    )

    valid_source_ids = {
        record.source_record_id
        for record in (*valid_gateway, *valid_bank, *valid_ledger)
    }
    valid_source_ids.update(
        f"src_{fingerprint}"
        for fingerprint in ()  # keep the set construction explicit
    )
    for section in (
        ground_truth["expected_settlement_to_bank_links"],
        ground_truth["expected_gateway_to_ledger_links"],
        ground_truth["expected_excluded_or_distractor_records"],
        ground_truth["expected_rejected_rows"],
    ):
        for item in section:
            candidates = [item]
            if "expected_bank_credit" in item and item["expected_bank_credit"]:
                candidates.append(item["expected_bank_credit"])
            if "gateway" in item:
                candidates.append(item["gateway"])
                candidates.extend(item.get("ledger_lines", []))
            if "source_records" in item:
                candidates.extend(item["source_records"])
            for candidate in candidates:
                source_id = candidate.get("source_record_id")
                if (
                    source_id
                    and source_id not in valid_source_ids
                    and candidate not in rejected
                ):
                    raise VerificationError(
                        f"ground-truth source reference does not resolve: {source_id}"
                    )

    from app.domain import ClosePolicy

    ClosePolicy.model_validate(policy)
    if manifest["record_counts"] != {
        "razorpay_recon": len(gateway_rows),
        "bank_statement": len(bank_rows),
        "general_ledger": len(ledger_rows),
    }:
        raise VerificationError("manifest record counts do not match files")
    if manifest["settlement_count"] != len(settlements):
        raise VerificationError("manifest settlement count mismatch")
    if dataset_kind in {"demonstration", "held_out"}:
        counts = manifest["record_counts"]
        if not 100 <= counts["razorpay_recon"] <= 120:
            raise VerificationError(
                "frozen gateway count is outside the documented range"
            )
        if not 12 <= counts["bank_statement"] <= 20:
            raise VerificationError("frozen bank count is outside the documented range")
        if not 180 <= counts["general_ledger"] <= 250:
            raise VerificationError(
                "frozen ledger count is outside the documented range"
            )
        if not 8 <= manifest["settlement_count"] <= 12:
            raise VerificationError(
                "frozen settlement count is outside the documented range"
            )
        if not REQUIRED_SCENARIO_IDS.issubset(
            set(ground_truth["required_scenarios_present"])
        ):
            raise VerificationError("frozen scenario catalogue is incomplete")
    _check_runtime_import_boundary()
    return {
        "dataset_kind": dataset_kind,
        "record_counts": manifest["record_counts"],
        "settlement_count": manifest["settlement_count"],
        "expected_close_readiness": ground_truth["expected_close_readiness"],
    }


__all__ = ["VerificationError", "verify_dataset"]

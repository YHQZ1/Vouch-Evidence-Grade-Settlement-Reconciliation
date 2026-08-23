# Canonical data contract

**Status:** Accepted for MVP  
**Schema version:** `v1`  
**Last reviewed:** 2026-08-23

## Purpose

This document defines the synthetic input contracts and canonical invariants used
by Vouch. Phase 2 implements the framework-independent contracts in
`backend/app/domain`; ingestion and fixtures remain later-phase work.

## Global conventions

- CSV is the initial input format.
- UTF-8 and LF line endings are required.
- Column names use `snake_case`.
- Raw columns and raw values are preserved exactly.
- Each ingested row receives a stable `source_record_id` derived from the source
  fingerprint and row number.
- Money uses integer currency subunits. INR values are represented in paise.
- Currency uses uppercase ISO 4217 codes.
- Canonical timestamps are UTC ISO 8601 values.
- Source Unix timestamps are interpreted as UTC.
- Display timezone is a batch preference and does not change stored timestamps.
- Empty values are null, never overloaded sentinel strings such as `NA` or `-`.
- Identifiers remain strings and are never numerically coerced.
- Ground-truth columns are prohibited in runtime input files.
- `source_row_number` means the one-based physical data-row number in the
  emitted CSV, excluding the header. The interpretation is identical for every
  source file and is used with the final file fingerprint to derive
  `source_record_id`.

## Phase 2 implementation boundary

- `Money` stores a signed integer `subunits` value and a supported ISO
  `Currency`; arithmetic rejects cross-currency operations and accepts no
  floating-point values. MVP records and policy are restricted to `INR`.
- `CanonicalTimestamp` stores aware UTC `datetime` values. Naive timestamps and
  non-integer Unix timestamps are rejected; source Unix seconds are interpreted
  as UTC.
- `SourceLineage` requires source kind, source name, SHA-256 fingerprint, row
  number, and schema version. `source_record_id` is derived as
  `src_<sha256(source_fingerprint + ':' + source_row_number)>` and a supplied
  conflicting ID is rejected.
- `RawEvidence` and every canonical record retain a copied, deterministically
  ordered, immutable mapping of CSV-safe `str | None` raw values. Canonical
  normalization never replaces that evidence.
- `GatewayMovement`, `BankEntry`, and `LedgerLine` preserve source lineage and
  expose signed derived movement without changing the unsigned source fields.
- `ClosePolicy` is an immutable, versioned input contract. It carries period,
  timezone, materiality, tolerance, SLA, balance-account, and configured ledger
  role inputs; it does not itself make a close decision.

## Input A: Razorpay settlement reconciliation

The synthetic source mirrors the documented Razorpay Settlement Recon response.

### Required fields

| Field           | Type           | Rule                                             |
| --------------- | -------------- | ------------------------------------------------ |
| `entity_id`     | string         | Unique transaction entity within the source      |
| `type`          | enum           | `payment`, `refund`, `transfer`, or `adjustment` |
| `debit`         | integer        | Non-negative currency subunits                   |
| `credit`        | integer        | Non-negative currency subunits                   |
| `amount`        | integer        | Non-negative source amount in currency subunits  |
| `currency`      | string         | `INR` in MVP                                     |
| `fee`           | integer        | Non-negative currency subunits                   |
| `tax`           | integer        | Non-negative currency subunits                   |
| `on_hold`       | boolean        | Source settlement-hold indicator                 |
| `settled`       | boolean        | Source settlement indicator                      |
| `created_at`    | timestamp      | Source event creation time                       |
| `settled_at`    | timestamp/null | Settlement time when settled                     |
| `settlement_id` | string/null    | Required for in-scope settled activity           |

### Supported optional fields

`description`, `notes`, `payment_id`, `settlement_utr`, `order_id`,
`order_receipt`, `method`, `card_network`, `card_issuer`, `card_type`,
`dispute_id`, `channel_type`, and `balance_account_id`.

### Canonical movement

```text
signed_net = credit - debit
```

The expected bank amount for a settlement is the sum of `signed_net` for all
eligible rows in that settlement and balance-account partition.

Vouch does not subtract `fee` or `tax` a second time from `credit`. These fields
are retained for explanation and ledger verification because the authoritative
source movement is already represented by `credit` and `debit`.

### Gateway invariants

- `debit` and `credit` cannot both be negative.
- A row with both values equal to zero is rejected unless a documented scenario
  explicitly permits it.
- Settled in-scope rows require `settled_at` and `settlement_id`.
- A settlement cannot span currencies.
- If present, `balance_account_id` is a hard partition key.
- Contradictory UTR values inside one settlement create an exception.
- Transaction type controls determine whether a debit or credit direction is
  plausible; unexpected direction is not silently normalized.

## Input B: bank statement

### Required fields

| Field         | Type      | Rule                                                |
| ------------- | --------- | --------------------------------------------------- |
| `bank_row_id` | string    | Unique within the bank source                       |
| `posted_at`   | timestamp | Bank posting time or date                           |
| `direction`   | enum      | `credit` or `debit`                                 |
| `amount`      | integer   | Positive currency subunits                          |
| `currency`    | string    | `INR` in MVP                                        |
| `narration`   | string    | Raw bank narration; may be empty but not fabricated |

### Optional fields

`value_date`, `reference`, `account_suffix`, and `balance_after`.

### Derived fields

- `normalized_utr`: optional normalization of an explicitly supplied UTR;
- `normalized_narration`: comparison representation while preserving raw text;
- `signed_amount`: positive for credit and negative for debit.

The Phase 2 domain contract does not infer UTRs from source text.

### Bank invariants

- A Razorpay settlement candidate must be a bank credit.
- Exact UTR requires normalized equality, not substring similarity.
- UTR agreement is validated with currency, amount, date window, and uniqueness.
- Unrelated bank transactions remain in the dataset as negative candidates.
- One bank row cannot clear two settlements unless a documented source policy
  explicitly permits aggregation.

## Input C: general ledger

### Required fields

| Field          | Type      | Rule                                 |
| -------------- | --------- | ------------------------------------ |
| `journal_id`   | string    | Source journal identifier             |
| `line_id`      | string    | Unique ledger line identity          |
| `posted_at`    | timestamp | Ledger posting time or date          |
| `account_code` | string    | Merchant-specific account identifier |
| `account_name` | string    | Raw merchant account label           |
| `debit`        | integer   | Non-negative currency subunits       |
| `credit`       | integer   | Non-negative currency subunits       |
| `currency`     | string    | `INR` in MVP                         |

### Optional fields

`reference`, `narration`, `order_id`, `payment_id`, `settlement_id`, `utr`, and
`voucher_type`.

### Configured canonical account roles

- `bank`
- `razorpay_clearing`
- `sales_revenue`
- `refunds`
- `gateway_fee_expense`
- `input_gst`
- `other`

The mapping from merchant account code to canonical role belongs to the batch
configuration. Vouch does not infer a universal chart of accounts.

### Ledger record invariants

- A line cannot contain both a positive debit and positive credit.
- Zero-value lines are preserved; later controls may classify them explicitly.

### Phase 4 journal and clearing controls

These requirements remain part of the accepted product contract, but are not
implemented by the Phase 2 record-local `LedgerLine` contract:

- Every journal must balance: total debit must equal total credit.
- An unbalanced journal is a blocking exception.
- Reference linking cannot override an accounting conflict.
- Clearing-account residuals are calculated for the selected close scope.
- The deterministic control engine includes journal-balance controls.
- The bounded investigation agent may request deterministic journal-balance
  validation; it cannot perform or override that validation itself.

## Batch policy contract

The implemented `ClosePolicy` contract defines:

| Field                           | Purpose                                     |
| ------------------------------- | ------------------------------------------- |
| `policy_version`                | Reproduce the decision rules used           |
| `period_start` / `period_end`   | Scope as timezone-aware UTC timestamps     |
| `display_timezone`              | User-facing date interpretation             |
| `currency`                      | `INR` for MVP                               |
| `balance_account_ids`           | Optional permitted partitions               |
| `amount_tolerance_subunits`     | Explicit rounding tolerance                 |
| `materiality_absolute_subunits` | Absolute blocking threshold                 |
| `materiality_relative_bps`      | Optional batch-relative threshold           |
| `settlement_sla`                | Explicit positive timing policy by class    |
| `account_role_mapping`          | Explicit non-null mapping to one of the seven ledger roles |

No threshold will be presented as universally correct. The demonstration policy
will be clearly labeled synthetic.

## Phase 4 runtime outputs

### Settlement result

Each result contains:

- settlement and balance-account identity;
- constituent source-record IDs;
- calculated gross activity and signed net;
- candidate and verified bank links;
- candidate and verified movement-level ledger links (one gateway source record
  and its exact same-journal ledger assignment per link);
- separate settlement-level bank/clearing posting links;
- clearing-account residual;
- resolution state and reason codes;
- exception severity and material value;
- resolver type; and
- complete decision lineage.

The runtime service returns an immutable `BatchResult` containing source
fingerprints, ingestion summaries and rejected rows, settlement aggregates,
accepted links, rejected candidates with signals and rejection reasons, excluded
records, accounting controls, exceptions, value buckets, close assessment,
decisions, and append-only audit events. The CLI serializes this contract as
canonical JSON. Runtime code does not read ground-truth data.

### Audit event

Each event contains:

- immutable event ID;
- batch ID;
- decision or case ID;
- before and after state;
- source-record IDs;
- input fingerprints;
- rule, schema, policy, and prompt versions;
- calculated values used by the decision;
- resolver type; and
- UTC timestamp.

The Phase 4 in-memory audit stream is ordered by deterministic sequence number
and includes source-ingestion, policy-validation, bank-candidate,
evidence-link, ledger-control, settlement-resolution, and final close-assessment
events in that causal order. Accepted and rejected bank candidates carry their
acceptance flag, score, signals, and machine-readable reasons. Duplicate source
identifiers are rejected for every occurrence; malformed ledger identifiers do
not prove out-of-scope status, while independently validated bank/gateway
balance-account attributes may. Fee and tax totals prefer authoritative
adjustment movements when the export also carries descriptive payment fields,
avoiding double counting; descriptive-only values require independently
verified configured ledger postings before `fee_tax_netted` can be emitted.
Every accepted or proposed movement-level ledger assignment has its own
evidence-link event and cites exactly one gateway source record plus its
assigned ledger source records. Ledger source records are never bundled across
movements. Settlement bank/clearing evidence is represented separately by a
settlement-level link with its journal ID. A proposed or rejected assignment or
link must contain at least one reason code. A verified movement assignment
requires one unique unused same-journal pair with the configured account role,
amount, identifiers, settlement scope, and debit/credit direction.

### Phase 5 evaluation artifacts

Evaluation artifacts are outside runtime source contracts and are loaded only by
the evaluation adapter. `runtime-result.json` is the canonical serialized
`BatchResult` and is written before ground truth is opened. The machine report
retains integer numerator and denominator for every ratio and deterministic
decimal/percentage strings. Money metrics use only absolute signed
settlement-net subunits. `metrics.json` and `summary.md` are deterministic;
`operational.json` holds measured duration, throughput, accepted source-record
count, and explicitly disabled/not-applicable model counters.

The adapter rejects malformed, stale, mismatched, or tampered runtime, manifest,
and ground-truth artifacts. It validates dataset identity, source fingerprints,
fixed evaluation clock, schema version, Phase 4 rule version, policy version,
and ground-truth schema version. Exact movement links retain the Phase 4
108-relationship boundary; settlement containment cannot create a movement true
positive. Phase 5 does not change runtime reconciliation policy or load labels
from `app/`.

## Ground-truth contract

Ground truth is stored separately from runtime sources and records:

- expected settlement-to-bank links;
- expected gateway-to-ledger links;
- expected resolution state;
- expected reason codes;
- seeded scenario identifier;
- auto-clear eligibility; and
- expected blocking behavior.

Runtime packages may not import ground-truth schemas or file locations.

Phase 3 emits runtime inputs under `data/<dataset>/inputs/`, runtime-only
manifests under `data/manifests/`, and the versioned answer key under
`data/ground_truth/<dataset>/`. Ground truth is constructed only after final
input bytes are written and fingerprinted, avoiding a circular dependency
between source-record IDs and answer-key content.

Phase 3 ground truth also records the unresolved value contributed by each
settlement and its policy-derived materiality result. A material unresolved
`needs_review` settlement blocks close; an absent bank credit that is still
within the configured SLA is `pending_within_sla` and may contribute to
`READY_WITH_EXCEPTIONS`. These are evaluation-only labels, not runtime policy
logic. The frozen batches use a 48-hour SLA and an absolute threshold of 10,000
paise or the configured relative threshold, whichever applies.
The shared reason-code vocabulary also distinguishes `fee_tax_netted` and
`refund_netted` from the generic `exact_evidence_verified` explanation.
Balance-account isolation is a clean partition control: an exact candidate in
the configured account remains valid while an otherwise similar candidate in a
different account is excluded.

## Synthetic scenario catalogue

The frozen evaluation batch must include:

1. clean multi-payment settlements;
2. normal fees and tax;
3. same-settlement and later-settlement refunds;
4. transfer and adjustment movements;
5. missing and corrupted UTRs;
6. valid bank arrival within SLA;
7. missing bank arrival after SLA;
8. duplicate and missing ledger lines;
9. incorrect fee or tax booking;
10. amount/date collisions;
11. unrelated bank distractors;
12. balance-account isolation;
13. malformed rows that must be rejected; and
14. untrusted narration that resembles model instructions;
15. amount resemblance without sufficient proof; and
16. a distinct pending-within-SLA case with no bank credit.

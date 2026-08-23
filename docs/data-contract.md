# Canonical data contract

**Status:** Accepted for MVP  
**Schema version:** `v1`  
**Last reviewed:** 2026-08-23

## Purpose

This document defines the synthetic input contracts and canonical invariants used
by Vouch. It is a design contract; actual schema models and fixtures will be added
during implementation.

## Global conventions

- CSV is the initial input format.
- UTF-8 and LF line endings are required.
- Column names use `snake_case`.
- Raw columns and raw values are preserved.
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

- `normalized_utr`: conservative extraction from `reference` or narration;
- `normalized_narration`: comparison representation while preserving raw text;
- `signed_amount`: positive for credit and negative for debit.

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
| `journal_id`   | string    | Groups balanced journal lines        |
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

### Ledger invariants

- Every journal must balance: `sum(debit) == sum(credit)`.
- A line cannot contain both a positive debit and positive credit.
- An unbalanced journal is a blocking exception.
- References support linking but do not override amount or accounting conflicts.
- Clearing-account residuals are calculated for the selected close scope.

## Batch policy contract

The versioned close policy will define:

| Field                           | Purpose                                     |
| ------------------------------- | ------------------------------------------- |
| `policy_version`                | Reproduce the decision rules used           |
| `period_start` / `period_end`   | Scope the close period                      |
| `display_timezone`              | User-facing date interpretation             |
| `currency`                      | `INR` for MVP                               |
| `balance_account_ids`           | Optional permitted partitions               |
| `amount_tolerance_subunits`     | Explicit rounding tolerance                 |
| `materiality_absolute_subunits` | Absolute blocking threshold                 |
| `materiality_relative_bps`      | Optional batch-relative threshold           |
| `settlement_sla`                | Timing policy by supported settlement class |
| `account_role_mapping`          | Ledger account code to canonical role       |

No threshold will be presented as universally correct. The demonstration policy
will be clearly labeled synthetic.

## Runtime outputs

### Settlement result

Each result contains:

- settlement and balance-account identity;
- constituent source-record IDs;
- calculated gross activity and signed net;
- candidate and verified bank links;
- candidate and verified ledger links;
- clearing-account residual;
- resolution state and reason codes;
- exception severity and material value;
- resolver type; and
- complete decision lineage.

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
14. untrusted narration that resembles model instructions.

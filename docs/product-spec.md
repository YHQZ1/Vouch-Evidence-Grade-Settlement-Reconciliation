# Product specification

**Status:** Accepted for MVP  
**Last reviewed:** 2026-08-23  
**Track:** Razorpay AI Buildathon — AI Finance Controller

## Product statement

Vouch is an evidence-grade settlement-close controller. It proves how a batch of
Razorpay activity moved through the bank and general ledger, safely investigates
ambiguous evidence, and tells a finance operator whether the batch is ready to
close.

## Target user

The primary user is a finance-operations analyst or controller at a merchant with
enough payment volume that settlement reconciliation is repetitive, material, and
difficult to review manually.

The initial user is assumed to:

- export Razorpay settlement reconciliation data;
- obtain a bank-statement export;
- obtain journal-level general-ledger data;
- understand the merchant's chart of accounts and materiality policy; and
- retain final authority over unresolved exceptions.

## Job to be done

> When I close a Razorpay settlement period, help me prove that every material
> settlement reached the bank and was represented correctly in the ledger, so I
> can close confidently without manually tracing every record.

## Problem boundaries

Vouch is responsible for settlement evidence and close readiness. It is not
responsible for initiating payments, moving funds, posting journals, certifying an
audit, or replacing the merchant's accounting policy.

The product reasons about three evidence sources:

1. Razorpay settlement reconciliation activity;
2. bank-statement entries; and
3. balanced general-ledger journal lines.

No single source is assumed to be correct in every case.

## Product thesis

The safest useful automation is selective:

- deterministic controls should resolve clear cases;
- ambiguous cases should be investigated rather than guessed;
- AI should interpret weakly structured evidence and propose hypotheses;
- deterministic verification should retain final authority; and
- unresolved material value should be visible in the close decision.

## User journey

### 1. Create a reconciliation batch

The operator selects a close period, currency, timezone, balance-account scope,
and materiality policy.

### 2. Supply evidence

The operator provides the Razorpay, bank, and ledger files. Vouch validates the
schemas, shows rejected rows, and refuses to continue when critical fields cannot
be interpreted safely.

### 3. Run controls

Vouch builds settlement aggregates, links supporting records, verifies accounting
invariants, and classifies each case.

### 4. Investigate exceptions

Only unresolved cases reach the investigation agent. The operator can inspect the
agent's hypothesis, the tools it used, and the deterministic verification result.

### 5. Review close readiness

Vouch reports verified value, explained value, in-flight value, unresolved value,
and material exceptions. The final close state is generated from an explicit
policy rather than model judgment.

### 6. Export evidence

The operator exports a reconciliation report, exception report, and machine-
readable audit record containing source lineage and input fingerprints.

### 7. Review through the Phase 7 interface

The review-only React interface exposes the complete lifecycle without adding a
second decision authority: an explicit clock and four immutable source slots,
policy-derived close readiness, settlement evidence flow, every material
exception, audit explanation, and canonical exports. It preserves API reason
codes and evidence statuses and presents exact integer-subunit amounts. It does
not provide manual clear/override controls, accounting writes, money movement,
authentication, or durable browser persistence. Its Phase 8 investigation panel
is explicit, read-only, limited to eligible `needs_review` cases, and cannot
create an effective state without deterministic verification.

## Resolution states

| State                      | Meaning                                                                            | Close treatment                          |
| -------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------- |
| `auto_cleared`             | All required deterministic evidence is present and consistent                      | Eligible to close                        |
| `cleared_with_explanation` | A known difference is completely explained and verified                            | Eligible to close                        |
| `pending_within_sla`       | Evidence is not complete, but the item is still within its expected arrival window | Visible, normally non-blocking           |
| `needs_review`             | Evidence is insufficient or multiple candidates remain                             | Policy-dependent, never silently cleared |
| `critical_exception`       | A material, overdue, duplicated, or contradictory item exists                      | Blocking                                 |
| `excluded`                 | The record is valid but outside the selected close scope                           | Excluded from denominator                |

## Close-readiness states

### `READY`

All in-scope material value is cleared and no blocking control failed.

### `READY_WITH_EXCEPTIONS`

Only explicitly permitted non-material or in-flight exceptions remain. Every such
exception is named and included in the proof packet.

### `BLOCKED`

At least one configured blocking condition is present, including a material
unresolved value, an overdue missing bank credit, a duplicate financial posting,
an unbalanced journal, or an evidence-integrity failure.

Thresholds are supplied by a versioned close policy. They are not hard-coded as
universal accounting rules.

## Functional requirements

### Input and validation

- **FR-001:** Accept one Razorpay reconciliation file, one bank file, and one
  ledger file per batch.
- **FR-002:** Preserve raw values and stable source-row identities.
- **FR-003:** Validate required fields, types, currency, and date ranges before
  reconciliation.
- **FR-004:** Fingerprint each source file and record the canonical schema version.
- **FR-005:** Reject unsafe ambiguity rather than silently coercing values.

### Reconciliation

- **FR-101:** Group Razorpay activity by settlement and optional balance account.
- **FR-102:** Calculate signed settlement net from credit minus debit.
- **FR-103:** Match settlements to bank entries using normalized UTR and
  independent validation controls.
- **FR-104:** Generate non-UTR candidates without auto-clearing them solely from
  similarity.
- **FR-105:** Link payment, refund, fee, tax, and settlement evidence to ledger
  journals.
- **FR-106:** Verify journal balance and Razorpay clearing-account residual.
- **FR-107:** Prevent one-to-many record reuse unless explicitly permitted by the
  accounting model.

### Investigation agent

- **FR-201:** Invoke AI only for cases unresolved by deterministic controls.
- **FR-202:** Restrict the agent to read-only evidence tools and a finite step
  budget.
- **FR-203:** Require schema-valid hypotheses with cited source-record IDs.
- **FR-204:** Pass every hypothesis through deterministic verification.
- **FR-205:** Mark a case `needs_review` when the model is unavailable, invalid,
  contradictory, or unsupported by evidence.
- **FR-206:** Never invoke AI for auto-cleared, explained, pending, critical, or
  excluded cases.
- **FR-207:** Retain base and effective verifier-owned states separately and
  export append-only investigation history without hidden model reasoning.
- **FR-208:** Expose server-owned eligibility and provider availability; never
  offer an action for a critical UTR-collision case or an accepted settlement.
- **FR-209:** Reserve accepted bank evidence atomically and single-use across
  the entire batch, including deterministic evidence already consumed.

### Reporting and audit

- **FR-301:** Report record-count and money-weighted metrics separately.
- **FR-302:** Rank exceptions by materiality, age, and control severity.
- **FR-303:** Explain each decision with reason codes and evidence references.
- **FR-304:** Produce close readiness from a versioned deterministic policy.
- **FR-305:** Export reconciliation, exceptions, and audit artifacts.

## Non-functional requirements

- **NFR-001 — Correctness:** Financial calculations use integer currency
  subunits and explicit signs.
- **NFR-002 — Reproducibility:** Identical inputs, configuration, and rule versions
  produce identical deterministic results.
- **NFR-003 — Auditability:** Every result is traceable to immutable source rows.
- **NFR-004 — Privacy:** No source data leaves the machine by default.
- **NFR-005 — Resilience:** The deterministic product remains useful when AI is
  disabled or unavailable.
- **NFR-006 — Performance:** A 50+ record batch completes interactively on a
  developer laptop, excluding optional model latency.
- **NFR-007 — Accessibility:** Status is communicated by text and structure, not
  color alone.

## Success criteria

The MVP is successful when it can:

- reconcile a frozen 50+ record synthetic batch end to end;
- produce a settlement proof packet for every in-scope settlement;
- achieve zero false auto-clears on the held-out evaluation batch;
- expose every seeded material discrepancy in the exception report;
- continue safely when the AI adapter is unavailable;
- reproduce all reported metrics from a documented command; and
- demonstrate one graceful agent abstention or verification rejection.

## Non-goals

- Full enterprise resource planning integration.
- Automatic journal posting.
- Bank or Razorpay write operations.
- Fraud detection or revenue recovery.
- General financial forecasting.
- Universal chart-of-accounts inference.
- Multi-currency accounting in the MVP.
- Production multi-tenancy, authentication, or authorization.

## MVP acceptance scenario

Given a fixed synthetic period containing clean settlements, fees, refunds,
transfers, adjustments, a bank delay, a missing overdue credit, a duplicate
journal, a corrupted reference, and an amount/date collision, Vouch must:

1. clear only the relationships supported by sufficient evidence;
2. classify the in-window delay as pending rather than missing;
3. block the close for the material overdue and duplicate cases;
4. allow the agent to investigate the corrupted reference;
5. reject the amount/date collision when uniqueness is not established; and
6. reproduce the expected metrics without reading ground-truth labels at runtime.

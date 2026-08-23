# ADR 0006: Use conservative deterministic reconciliation and policy close readiness

**Status:** Accepted  
**Date:** 2026-08-23

## Context

Settlement evidence arrives as independent gateway, bank, and ledger files. A
reference or amount resemblance can be coincidental, and accounting integrity
failures must not be hidden by a successful bank match. Phase 4 also needs to be
useful without AI, persistence, or a system clock.

## Decision

Phase 4 fingerprints source bytes before strict parsing, preserves raw rows and
one-based lineage, and aggregates settled gateway movements by settlement,
balance account, and currency using `credit - debit`. Bank clearing requires
normalized UTR agreement plus independent credit direction, currency, amount
tolerance, balance-account partition, SLA timing, uniqueness, and one-use checks.
Missing or conflicting UTR evidence produces explicit candidates and never clears
by score, amount, date, or narration alone.

Ledger roles come only from `ClosePolicy.account_role_mapping`. Journal balance,
duplicate/missing lines, fee/tax role correctness, required settlement postings,
and clearing residuals are deterministic controls. The state precedence is:
excluded scope; critical integrity or overdue conditions; pending within SLA;
verified refund explanation; verified exact evidence (including fee/tax netting);
then needs review. Source rows with malformed or duplicated in-scope business
identifiers are rejected in all occurrences and block close. Close readiness is
policy-derived: blocking conditions win, permitted pending or non-material
exceptions produce `READY_WITH_EXCEPTIONS`, and only an unblocked fully eligible
batch is `READY`.

Descriptive fee and tax fields on payment rows are explanatory data, not proof.
When explicit adjustment movements are absent, the fee and tax totals require
unique, balanced, same-journal configured expense/GST and clearing postings;
otherwise the corresponding booking mismatch is blocking. Explicit adjustment
movements remain the authoritative source for the frozen fee and tax totals.

Ledger evidence is assigned at movement granularity. Each
`gateway_to_ledger` link contains exactly one gateway source record, the exact
ledger source records assigned to it, and their common journal ID. The matcher
consumes an accepted journal pair once; swapped, reused, ambiguous, duplicate,
missing, or unrelated lines cannot satisfy another movement. Bank and clearing
postings for the settlement itself are emitted separately as a
`settlement_to_ledger` link, so settlement-level evidence cannot masquerade as
movement evidence.

The required movement invariant is strict for payments, refunds, transfers, and
adjustments: exactly one unused same-journal pair must match the movement's
identifiers, amount, configured counterpart role, settlement scope, and posting
direction. Candidate lines with a role or direction mismatch are retained as
proposed evidence with `ledger_account_role_mismatch` or
`ledger_direction_mismatch`; they add a blocking accounting reason and cannot
leave a settlement cleared. Domain validators reject proposed or rejected
assignments and links that omit reason codes.

Every result is immutable in memory and includes source fingerprints, evidence
links, rejected candidates, reason codes, rule/policy/schema versions, explicit
evaluation clock, deterministic IDs, sequence numbers, and append-only audit
events for ingestion, candidate generation, accepted/proposed links, ledger
controls, settlement decisions, and close assessment. Accepted bank links retain
all candidate signals; rejected candidates retain machine-readable reasons. The
service performs no persistence or external writes.

The demonstration contract is checked exactly at this boundary: all 108 frozen
gateway-to-ledger movement relationships must map one-to-one by gateway source
record, journal ID, and present ledger source IDs. A broad subset match is not
considered sufficient evidence of lineage.

Audit events are emitted in causal stages: source ingestion and policy
validation, bank candidates, evidence links, ledger controls, settlement
resolutions, and final close assessment. Settlement decision sequence numbers
are local settlement ordering; audit event sequence numbers are one global,
contiguous stream.

## Consequences

Positive:

- false auto-clears are constrained by independent evidence;
- balance-account adversaries cannot contaminate valid in-partition matches;
- unresolved value and close treatment remain visible and reproducible; and
- the deterministic path remains available when AI is disabled.

Costs:

- some legitimate relationships without strong identifiers remain needs-review;
- source-row reordering changes row lineage fingerprints even when semantic
  aggregate identities and states remain stable; and
- persistence, evaluation metrics, and human review workflows remain future work.

## Alternatives considered

### Similarity threshold auto-clearing

Rejected because amount/date/narration resemblance does not prove identity and
can transfer a relationship from another record.

### Identifier-only bank joins

Rejected because UTR must agree with independent attributes and uniqueness.

### Model-led reconciliation

Deferred to Phase 8; any future hypothesis must pass the same deterministic
verification boundary.

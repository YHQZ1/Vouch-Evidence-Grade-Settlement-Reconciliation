# ADR 0002: Model settlement ID, UTR, bank, and ledger as distinct evidence

**Status:** Accepted  
**Date:** 2026-08-23

## Context

A Razorpay settlement contains multiple transaction movements. The settlement ID
groups those internal rows, while UTR is the bank-traceable reference used to find
the corresponding bank credit. Ledger journals form a third, merchant-controlled
evidence source with different identifiers and accounting structure.

Treating any one identifier as a universal join key would misrepresent the actual
data model and create unsafe matches.

## Decision

Vouch will:

- group Razorpay movements by `settlement_id` and optional balance account;
- calculate expected settlement net as `sum(credit) - sum(debit)`;
- use normalized UTR as strong settlement-to-bank evidence;
- independently verify amount, direction, currency, time, and uniqueness;
- use order, payment, settlement, UTR, journal, and account evidence for ledger
  relationships according to their appropriate scope; and
- represent each relationship as an evidence link with a proposed or verified
  state.

Missing UTR may trigger candidate generation. Amount and date similarity alone
cannot produce a verified bank link.

## Consequences

- The domain model is more explicit than a flat joined table.
- One settlement can preserve lineage to many underlying gateway and ledger rows.
- The system can explain why two different amounts or dates belong to the same
  economic flow.
- Synthetic data must model transaction, settlement, bank, and ledger identities
  separately.

## Alternatives considered

### Join bank directly on settlement ID

Rejected because a bank statement generally exposes bank reference and narration,
not Razorpay's internal settlement ID as a universal structured column.

### Match solely on amount and date

Rejected because repeated values and settlement timing create collisions.

### Recalculate bank net from amount minus fee and tax for every row

Rejected because transaction types differ and the recon source already provides
authoritative debit and credit movement fields.

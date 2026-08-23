# ADR 0005: Use immutable canonical domain contracts and integer subunits

**Status:** Accepted  
**Date:** 2026-08-23

## Context

Phase 2 is the trust boundary between untrusted CSV-shaped rows and future
reconciliation controls. Silent coercion, mutable raw evidence, local-time
interpretation, or floating-point arithmetic would make later decisions hard to
reproduce and could hide a false financial relationship.

## Decision

Vouch will use framework-independent, frozen Pydantic models for the canonical
domain boundary. Monetary fields are strict integer currency subunits. Source
rows carry a SHA-256 fingerprint, row number, schema version, and derived stable
source-record ID, while raw values are copied into a deterministically ordered,
scalar-only immutable mapping. Canonical timestamps must be timezone-aware and
are normalized to UTC. Gateway, bank, and ledger records retain unsigned source
movements and expose signed values only as deterministic record-local derived
properties. Close policy is an immutable, explicitly configured versioned input
contract, separate from the service that evaluates it.

## Consequences

- Invalid money, timestamps, source identities, and record invariants fail at the
  domain boundary.
- Raw evidence cannot be overwritten through ordinary model mutation.
- Later services can calculate movement net as `credit - debit` without
  reinterpreting source fields.
- The domain remains testable without FastAPI, a database, or an AI provider.
- CSV parsing and source-specific coercion must be implemented explicitly in the
  later ingestion phase.
- Phase 4 will add deterministic journal-balance, reference-conflict, and
  clearing-account residual controls; this ADR does not implement those
  aggregate controls in Phase 2.

## Alternatives considered

### Floating-point or decimal-only monetary fields

Rejected because the MVP contract is integer paise and deterministic signed
arithmetic; a later ingestion parser can produce an explicit integer subunit
value without weakening the domain boundary.

### Mutable dictionaries on frozen models

Rejected because a frozen outer model would still allow raw evidence or policy
maps to be changed through a nested dictionary or exposed backing store.

### Source-text interpretation during canonicalization

Deferred because source-text interpretation belongs to ingestion and matching
controls. Phase 2 only preserves an explicitly supplied UTR with conservative
case and surrounding-whitespace normalization.

### Naive timestamps interpreted in local time

Rejected because timing and SLA evidence must not depend on the developer's
machine timezone.

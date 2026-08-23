# ADR 0008: Expose deterministic reconciliation through a synchronous batch API

**Status:** Accepted  
**Date:** 2026-08-24

## Context

Phase 4 owns reconciliation policy and Phase 5 owns evaluation and labels. Phase
6 needs an HTTP boundary that accepts the four runtime sources, preserves
evidence, runs the deterministic service, and exposes reviewable artifacts
without moving financial decisions into route handlers.

## Decision

Vouch exposes versioned FastAPI routes under `/api/v1` and keeps `/healthz`
unchanged. Routes validate HTTP concerns, call an injected
`BatchWorkflowService`, map safe application errors, and serialize typed
contracts. `ReconciliationService` remains the deterministic authority.

The workflow uses `awaiting_sources → ready → running → completed | failed`.
A batch requires one gateway CSV, bank CSV, ledger CSV, and policy JSON upload.
Uploads are bounded, UTF-8 checked, parsed by the existing ingestion adapters,
fingerprinted with SHA-256, and stored as immutable bytes with content type and
filename. Client filenames are metadata only; reconciliation uses generated
internal workspace filenames, so client input is never used as a filesystem
path.

The repository is an injectable, concurrency-safe in-memory implementation.
Reconciliation is synchronous and receives the batch's explicit evaluation
clock. A completed result is immutable and repeated run requests return it. An
identical upload retry is idempotent; a different replacement is rejected with
`409`. A failed run stores only safe failure metadata and never stores a partial
result.

Phase 6 deliberately adds no PostgreSQL, SQLite, Redis, queue, cloud storage,
authentication, authorization, or external integration. Batches, source bytes,
and results do not survive process restart. A future persistence adapter may
implement the same repository contract without changing reconciliation policy.

## Consequences

- The complete deterministic demonstration is runnable with curl or `TestClient`.
- API responses and exports retain integer money subunits and source lineage.
- Lifecycle timestamps are operational metadata; the reconciliation clock is
  always explicit and is never read from the system clock.
- Local API access has no identity or tenant boundary and is suitable only for
  the local Phase 6 demo.

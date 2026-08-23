# ADR 0004: Use a local modular architecture with SQLite

**Status:** Accepted  
**Date:** 2026-08-23

## Context

The MVP processes a synthetic batch of roughly 50–120 transaction movements on a
single developer machine. It requires reliable evidence storage and audit queries,
but not distributed scale. Additional services would increase setup and failure
surface without improving the judged outcome.

## Decision

Vouch will use:

- a Python and FastAPI backend;
- framework-independent domain services;
- pandas for tabular ingestion and batch transformations;
- SQLite through SQLAlchemy for local persistence;
- a React and TypeScript interface; and
- ordinary HTTP between UI and backend.

Reconciliation policy will remain separate from API handlers, persistence models,
and UI components.

## Consequences

- The complete demo can run locally without external infrastructure.
- SQLite provides portable audit persistence and reproducible review.
- Domain functions remain testable without a running API or database.
- A future production database can replace the repository implementation without
  changing reconciliation policy.

## Alternatives considered

### Postgres, Redis, and a task queue

Rejected for the MVP because the workload does not justify their operational
cost.

### Streamlit-only application

Rejected because the intended evidence review and exception workflow benefit from
a deliberate React interface and an explicit API boundary.

### Graph database

Rejected because the evidence graph is small and can be represented relationally
without adding another runtime.

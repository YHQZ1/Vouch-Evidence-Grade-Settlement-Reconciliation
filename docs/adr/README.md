# Architecture decision records

Architecture decision records capture decisions that materially affect Vouch's
correctness, trust boundaries, data model, dependencies, or deployment shape.

## Status values

- `Proposed` — under review and not binding.
- `Accepted` — current implementation direction.
- `Superseded` — replaced by a later ADR.
- `Rejected` — considered and deliberately not adopted.

## Index

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-deterministic-first-selective-automation.md) | Use deterministic-first selective automation | Accepted |
| [0002](0002-settlement-evidence-linkage.md) | Model settlement ID, UTR, bank, and ledger as distinct evidence | Accepted |
| [0003](0003-bounded-provider-isolated-ai.md) | Keep AI bounded, local-first, and provider-isolated | Accepted |
| [0004](0004-local-modular-architecture.md) | Use a local modular architecture with SQLite | Accepted |
| [0005](0005-immutable-canonical-domain-contracts.md) | Use immutable canonical domain contracts and integer subunits | Accepted |
| [0006](0006-phase4-deterministic-reconciliation.md) | Use conservative deterministic evidence precedence and policy close readiness | Accepted |
| [0007](0007-phase5-evaluation-isolation-and-deterministic-reports.md) | Isolate evaluation and publish deterministic reports | Accepted |
| [0008](0008-fastapi-batch-boundary.md) | Expose deterministic reconciliation through a synchronous batch API | Accepted |
| [0009](0009-phase7-evidence-first-react-review-interface.md) | Build a review-only evidence-first React interface | Accepted |
| [0010](0010-phase8-bounded-investigation-runtime.md) | Keep bounded investigation append-only and verifier-owned | Accepted |

## Creating an ADR

Create a zero-padded Markdown file with:

1. title and status;
2. context;
3. decision;
4. consequences;
5. alternatives considered; and
6. links to any superseded decision.

Do not rewrite the outcome of an accepted ADR. Supersede it with a new record so
the project's reasoning remains auditable.

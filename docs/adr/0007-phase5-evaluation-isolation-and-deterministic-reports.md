# ADR 0007: Isolate evaluation and publish deterministic reports

**Status:** Accepted  
**Date:** 2026-08-24

## Context

Vouch must measure the Phase 4 deterministic engine without allowing answer-key
labels to influence runtime behavior. A metric is not reproducible if its
denominator, money basis, source lineage, or artifact identity is implicit. A
release decision also needs to fail safely when a false auto-clear, missing
material exception, invalid lineage, incompatible record reuse, or stale input
is found.

## Decision

Phase 5 lives under `backend/evaluation/` and is excluded from the application
wheel. The runtime `app/` package has no imports of evaluation, synthetic-data,
or ground-truth modules. The harness validates the runtime manifest and source
fingerprints, runs the Phase 4 engine with the manifest's fixed clock, writes
canonical `runtime-result.json`, verifies it contains no label-only fields, and
only then loads labels through the evaluation-only adapter.

Ground truth is independently typed and checked against its own artifact hash,
dataset identity, generator version, seed, clock, source fingerprints, policy
version, and ground-truth schema version. Runtime results are parsed as the
immutable Phase 4 contract and must be byte-identical to canonical JSON. Scoring
uses exact source-record relationships and statuses; settlement-wide containment
cannot create a movement-level true positive. Duplicate predictions are
deduplicated for counts and reported separately.

All money metrics use the absolute value of signed settlement net in integer
currency subunits. Ratios retain integer numerator and denominator; decimal and
percentage strings are produced with `Decimal`, and a zero denominator is
explicitly `not_applicable`. Operational wall-clock measurements are isolated
in `operational.json` and never enter deterministic reports.

`metrics.json` and `summary.md` contain no current timestamps, durations,
temporary paths, or random IDs. The renderer is invoked twice and its bytes are
compared. Applicable release gates fail the command with a non-zero exit code.
AI invalid-output and abstention gates are explicitly not applicable and remain
deferred to Phase 8.

## Consequences

- Public metrics can be regenerated from a clean checkout without label leakage.
- Held-out accuracy claims are distinct from demonstration walkthrough results.
- Exact lineage and source reuse remain safety gates, not descriptive metrics.
- Evaluation code is intentionally not available to the runtime wheel.
- Phase 6 APIs, persistence, frontend, AI, and production integrations remain
  outside this phase.

## Metric denominator contract

- Match rate: correctly and validly automated-cleared eligible settlements /
  settlements labelled `auto_clear_eligibility`.
- Auto-clear precision: correct automated clear decisions /
  all automated clear decisions; both automated clear states are included.
- Auto-clear coverage: automated clear decisions on eligible settlements /
  all eligible settlements.
- Bank-link precision and recall: exact verified settlement-to-bank source
  relationships against exact expected verified relationships.
- Gateway-to-ledger precision and recall: exact verified movement relationships
  including gateway source ID, exact ledger source IDs, settlement, and journal.
- Exact state accuracy: exact observed resolution state / labelled settlements.
- Exception recall: surfaced blocking, material exceptions with an expected
  reason / seeded material blocking exceptions.
- Money-weighted reconciliation: correctly cleared absolute settlement-net /
  total absolute settlement-net in scope.


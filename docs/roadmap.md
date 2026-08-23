# Delivery roadmap

**Status:** Proposed execution sequence  
**Last reviewed:** 2026-08-23

The roadmap is ordered by dependency and evaluation value. UI polish and AI are
deliberately downstream of the deterministic data and control model.

## Phase 0 — Product and repository contract

**Outcome:** The problem, scope, trust model, data contract, evaluation protocol,
and architecture decisions are reviewable before implementation.

- [x] Root product narrative
- [x] Product specification
- [x] Architecture and trust boundaries
- [x] Canonical data contract
- [x] Evaluation protocol
- [x] Safety model
- [x] Initial architecture decisions
- [x] Contribution and repository guidance

## Phase 1 — Synthetic evidence and ground truth

**Outcome:** A reproducible dataset generator creates realistic source files and a
separate answer key.

- [ ] Define canonical schema models
- [ ] Define scenario and reason-code registry
- [ ] Implement a deterministic seeded generator
- [ ] Generate readable development fixtures
- [ ] Freeze a 50+ record demonstration batch
- [ ] Freeze a separate held-out batch
- [ ] Verify ledger balance and settlement arithmetic independently
- [ ] Prove that runtime inputs contain no ground-truth fields

**Exit gate:** Dataset invariants pass without a reconciliation engine.

## Phase 2 — Deterministic reconciliation core

**Outcome:** Clear cases reconcile without AI and ambiguous cases become explicit
exceptions.

- [ ] Strict ingestion and row-level validation
- [ ] Raw evidence preservation and file fingerprinting
- [ ] Settlement and balance-account aggregation
- [ ] UTR-based bank matching and independent verification
- [ ] Ledger journal and clearing-account controls
- [ ] Candidate generation for unresolved records
- [ ] Append-only decision and audit model
- [ ] Versioned close-readiness policy

**Exit gate:** All deterministic development fixtures produce their expected
states with no false auto-clears.

## Phase 3 — Evaluation harness

**Outcome:** Every public metric is reproducible from stored results and isolated
ground truth.

- [ ] Evaluation-only label adapter
- [ ] Link and resolution metrics
- [ ] Money-weighted metrics
- [ ] Exception and close-readiness scoring
- [ ] Property and metamorphic tests
- [ ] Machine-readable and human-readable reports
- [ ] Clean-checkout evaluation command

**Exit gate:** The held-out deterministic run passes the release gates documented
in `evaluation.md`.

## Phase 4 — API and review interface

**Outcome:** A reviewer can run a batch, inspect evidence, understand exceptions,
and export the audit artifacts.

- [ ] FastAPI batch lifecycle
- [ ] Upload validation experience
- [ ] Close-readiness overview
- [ ] Settlement evidence view
- [ ] Materiality-ranked exception queue
- [ ] Audit explanation drawer
- [ ] Accessible status and error presentation
- [ ] Reconciliation, exception, and audit exports

**Exit gate:** The complete deterministic demo can be performed through the UI.

## Phase 5 — Bounded investigation agent

**Outcome:** The ambiguous tail receives useful investigation without expanding
the model's financial authority.

- [ ] Provider-isolated local model adapter
- [ ] Read-only investigation tools
- [ ] Structured hypothesis contract
- [ ] Step, time, and evidence-scope limits
- [ ] Deterministic hypothesis verifier
- [ ] Invalid-output, prompt-injection, and model-offline tests
- [ ] Agent audit and latency metrics

**Exit gate:** The agent resolves at least one seeded ambiguous case through
verified evidence and safely abstains or is rejected on another.

## Phase 6 — Submission readiness

**Outcome:** A reviewer can understand, run, verify, and evaluate Vouch from a
clean checkout.

- [ ] Reproducible local setup
- [ ] Pinned dependencies and model configuration
- [ ] CI quality and evaluation gates
- [ ] Architecture diagram synchronized with implementation
- [ ] Final held-out evaluation artifacts
- [ ] Five-minute pitch and demo script
- [ ] Public repository hygiene and secret scan
- [ ] Known limitations and responsible-use review

## Deferred work

- International settlement timing and currency conversion
- Instant and Smart Settlement policy
- Live Razorpay test-mode ingestion
- Merchant-specific schema onboarding
- Human review workflow and authorization
- Production database, tenancy, and retention controls
- Accounting-system integrations

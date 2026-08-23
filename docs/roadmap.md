# Delivery roadmap

**Status:** Proposed execution sequence  
**Last reviewed:** 2026-08-23

The roadmap is the locked eight-phase implementation sequence. Phase 0 is the
completed product and repository contract and is not counted among the eight
implementation prompts, which run from Phase 1 through Phase 8. The sequence is
ordered by dependency and evaluation value; UI polish and AI are deliberately
downstream of the deterministic data and control model.

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

## Phase 1 — Backend foundation

**Outcome:** A production-quality local Python backend foundation provides an
explicit application boundary, typed configuration, basic logging, and a stable
health check for future phases.

- [x] FastAPI application factory and entry point
- [x] Stable `GET /healthz` endpoint
- [x] Environment-backed typed settings with safe development defaults
- [x] Basic application logging configuration
- [x] Dependency, pytest, and Ruff configuration
- [x] Backend setup and verification documentation

**Exit gate:** The backend imports and starts locally, its health contract and
configuration behavior are tested, and no reconciliation behavior is present.

## Phase 2 — Canonical schemas and financial value objects

**Outcome:** Runtime inputs and financial values have explicit, deterministic,
framework-independent contracts.

- [x] Define canonical schema models for gateway, bank, and ledger records
- [x] Define integer currency-subunit value objects and signed arithmetic
  contracts
- [x] Define canonical timestamp, identifier, and normalization contracts
- [x] Define schema-version and source-row lineage contracts

**Exit gate:** Schema and value-object invariants pass independently, preserve raw
evidence, and never represent money with floating-point values.

## Phase 3 — Synthetic dataset and separate ground truth

**Outcome:** A reproducible dataset generator creates realistic source files and a
separate answer key.

- [x] Define scenario and reason-code registry
- [x] Implement a deterministic seeded generator
- [x] Generate readable development fixtures
- [x] Freeze a 50+ record demonstration batch
- [x] Freeze a separate held-out batch
- [x] Verify ledger balance and settlement arithmetic independently
- [x] Prove that runtime inputs contain no ground-truth fields

**Exit gate:** Dataset invariants pass without a reconciliation engine. The
checked-in batches are byte-for-byte reproducible from seeds `3102` and `3103`.

## Phase 4 — Deterministic reconciliation engine

**Outcome:** Clear cases reconcile without AI and ambiguous cases become explicit
exceptions.

- [x] Strict ingestion and row-level validation
- [x] Raw evidence preservation and file fingerprinting
- [x] Settlement and balance-account aggregation
- [x] UTR-based bank matching and independent verification
- [x] Ledger journal and clearing-account controls
- [x] Candidate generation for unresolved records
- [x] Append-only decision and audit model
- [x] Versioned close-readiness policy

**Exit gate:** The deterministic development fixtures produce their expected
states, the demonstration scenarios are reconciled without runtime labels, and
the engine has no false auto-clears in the Phase 4 test cases.

## Phase 5 — Evaluation harness

**Outcome:** Every public metric is reproducible from stored results and isolated
ground truth.

- [x] Evaluation-only label adapter
- [x] Link and resolution metrics
- [x] Money-weighted metrics
- [x] Exception and close-readiness scoring
- [x] Property and metamorphic tests
- [x] Machine-readable and human-readable reports
- [x] Clean-checkout evaluation command

**Exit gate:** The held-out deterministic run passes the applicable deterministic
release gates documented in `evaluation.md`. AI-specific gates remain deferred
to Phase 8.

## Phase 6 — FastAPI application layer

**Outcome:** The deterministic workflow is available through explicit HTTP
contracts without moving reconciliation policy into route handlers.

- [ ] FastAPI batch lifecycle and HTTP contracts
- [ ] Upload validation and source-ingestion endpoints
- [ ] Reconciliation-run and close-readiness endpoints
- [ ] Reconciliation, exception, and audit export endpoints
- [ ] API error, status, and integration contracts

**Exit gate:** The complete deterministic demo can be run through the API with
thin route handlers and explicit validation failures.

## Phase 7 — React review interface

**Outcome:** A reviewer can inspect evidence, understand exceptions, and review
close readiness through an accessible interface backed by the API.

- [ ] Close-readiness overview
- [ ] Settlement evidence view
- [ ] Materiality-ranked exception queue
- [ ] Audit explanation drawer
- [ ] Accessible status and error presentation
- [ ] API integration, loading states, and safe failure states

**Exit gate:** The complete deterministic demo can be performed through the
review interface with every material exception and decision explanation visible.

## Phase 8 — Bounded AI investigation agent

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

## Submission readiness — final release checklist

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

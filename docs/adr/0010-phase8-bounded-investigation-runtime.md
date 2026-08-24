# ADR 0010: Bounded investigation is an append-only verifier projection

**Status:** Accepted  
**Date:** 2026-08-24

## Context

The deterministic Phase 6 result is already the financial authority. The
ambiguous settlement tail benefits from local model-assisted evidence gathering,
but model output, source narration, and provider availability are untrusted.

## Decision

Phase 8 uses a provider-independent `InvestigationModel` protocol with a
disabled adapter as the default and a loopback-only Ollama-compatible adapter as
the optional implementation. A server-created allowlist and a closed,
read-only tool registry scope every run to one eligible `needs_review`
settlement. The model can request tools, submit one narrow settlement-to-bank
hypothesis, or abstain within hard step, time, response, and schema-retry
limits.

Only deterministic verification can append an `agent_verified` decision. An
accepted run creates a separate `cleared_with_explanation` effective-review
projection and a separate post-investigation close assessment. The immutable
base `BatchResult`, base decision, and deterministic exports are never rewritten.
Failed, rejected, abstained, cancelled, and unavailable runs remain in the
append-only process-local investigation repository. Restart loss remains an
explicit limitation.

Run finalization is one repository transaction: the run, single-use bank-source
reservation, optional effective decision, and audit event are committed under
one lock. Existing deterministic bank links seed the reservation set, so the
same bank evidence cannot be accepted for a second settlement. Provider calls
run behind a per-run deadline and bounded provider slot; late or trickling
results are ignored. Public HTTP cancellation is not exposed; internal
per-run cancellation is limited to the orchestration boundary.

Only source records actually returned by an appropriate tool become observed.
The summary tool returns metadata and observes no source records. Acceptance
requires candidate, canonical aggregate, ledger, and timing tool evidence, and
the hypothesis must cite the complete verifier input set: the candidate,
aggregate members, linked ledger records, and settlement-posting records.

The optional Ollama adapter is strict HTTP loopback-IP-only, disables proxies and
redirects, and rejects an over-limit initial request before opening a socket.
Effective review constructs one batch-wide projection, and the runtime export is
persisted before evaluation-only labels are opened.

## Consequences

- AI-disabled reconciliation remains on the existing deterministic path.
- Local provider failures never fail the reconciliation batch.
- The collision and all higher-authority controls remain unresolved.
- Structured traces are auditable without retaining hidden reasoning.
- Effective projections preserve unrelated exceptions and recompute close
  readiness from the resulting settlement collection.
- A durable adapter can be added later behind the repository protocol.

## Rejected alternatives

- Direct model authority over settlement state: rejected because it violates the
  product invariant.
- General agent framework: rejected because fixed orchestration is smaller and
  easier to audit.
- Cloud fallback: rejected because local-first privacy and availability are
  explicit requirements.

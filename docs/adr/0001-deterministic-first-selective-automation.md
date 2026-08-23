# ADR 0001: Use deterministic-first selective automation

**Status:** Accepted  
**Date:** 2026-08-23

## Context

Financial reconciliation includes many cases that can be proven through exact
identifiers, signed arithmetic, timing rules, journal balance, and uniqueness.
Language models are probabilistic and can produce plausible but unsupported
relationships. A model-first matcher would be difficult to reproduce, audit, and
defend under review.

## Decision

Vouch will run deterministic controls before invoking AI. Exact and accounting
controls may clear a case. Fuzzy methods may generate candidates but cannot clear
a case independently. AI is invoked only for the unresolved tail, and every AI
hypothesis must pass a deterministic verifier before it can affect resolution.

When verification is not possible, Vouch abstains and creates an exception.

## Consequences

Positive:

- clear cases are fast, reproducible, and inexpensive;
- every automated decision can cite concrete evidence;
- model unavailability does not prevent the core workflow;
- false-clear risk is isolated and measurable; and
- unresolved cases remain honest rather than forced.

Costs:

- more domain and rule engineering is required;
- coverage may initially be lower than an unconstrained fuzzy matcher; and
- agent-resolved cases require a separate verification layer.

## Alternatives considered

### LLM-first reconciliation

Rejected because it expands probabilistic authority, increases latency, and makes
the result difficult to reproduce.

### Deterministic-only reconciliation

Rejected as the final product direction because weakly structured narration and
ambiguous exception investigation can benefit from bounded semantic reasoning.
The deterministic-only mode remains a required safe fallback.

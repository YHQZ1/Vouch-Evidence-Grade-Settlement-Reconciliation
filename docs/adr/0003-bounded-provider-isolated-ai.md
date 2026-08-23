# ADR 0003: Keep AI bounded, local-first, and provider-isolated

**Status:** Accepted  
**Date:** 2026-08-23

## Context

The Buildathon asks for meaningful AI, but settlement evidence is sensitive and
model availability cannot be assumed. The initial local Ollama runtime also needs
environment verification. Binding the product directly to one model or SDK would
make the financial workflow fragile.

## Decision

Vouch will define a narrow investigation interface independent of the model
provider. The default implementation will target a local Ollama-compatible HTTP
endpoint with structured JSON-schema output.

The agent receives only a scoped exception package, uses read-only deterministic
tools, and operates under step and time limits. It can propose a hypothesis or
abstain. It cannot clear a case, change policy, access arbitrary files, execute
code, or call the network beyond the configured local model endpoint.

The core application must run to completion when the adapter is disabled.

## Consequences

- Financial records remain local by default.
- The exact local model can change without changing domain logic.
- Model failures become observable exception metadata rather than batch failures.
- Structured output and deterministic verification are required.
- Direct framework coupling to LangChain, CrewAI, or similar orchestration systems
  is unnecessary for the MVP.

## Alternatives considered

### Cloud-model dependency

Rejected for the MVP because it introduces credentials, cost, network dependency,
and data-boundary concerns.

### Hard-code the Ollama SDK into domain services

Rejected because it couples financial workflow behavior to one runtime.

### Remove AI entirely

Rejected because interpreting weakly structured evidence and planning bounded
exception investigation are meaningful model-assisted tasks when verification
retains final authority.

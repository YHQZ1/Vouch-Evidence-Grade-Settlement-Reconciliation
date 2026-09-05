# ADR 0011: Docker Compose reaches host Ollama through one explicit alias

**Status:** Accepted
**Date:** 2026-09-05

## Context

Vouch already permits an optional Ollama adapter on a loopback IP. Inside the
backend container, however, `127.0.0.1` names the container rather than the
developer's host, so the existing boundary cannot reach a host Ollama process.
Embedding a model in the Vouch images would also make builds large and slow.

## Decision

This ADR supersedes ADR 0010 only for endpoint transport. Its append-only model
workflow, deterministic verifier authority, and remaining safety controls stay in
force.

Docker Compose enables the Ollama investigation adapter and points it to
`http://host.docker.internal:11434`. The backend service maps that exact name to
Docker's host gateway for cross-platform Compose support. Runtime validation
allows this exact alias only when the separate
`VOUCH_AI_ALLOW_DOCKER_HOST_GATEWAY` capability is enabled. Loopback IP literals
remain accepted; arbitrary DNS names and non-loopback IPs remain rejected.
Proxies and redirects stay disabled.

The model remains a host prerequisite and is not part of either Vouch image.
Compose defaults to `llama3.2:3b` and a bounded 60-second investigation deadline.
Operators may disable the adapter with `VOUCH_AI_ENABLED=false` without affecting
deterministic reconciliation.

## Consequences

- A Compose-launched backend can use a locally installed Ollama model.
- Container images and CI do not download or package model weights.
- Ollama must listen on a host interface reachable from Docker; this is for a
  trusted development machine and must not expose port `11434` publicly.
- Provider unavailability remains a safe, explicit investigation outcome.
- The deterministic verifier remains the only authority that can accept a model
  hypothesis.

## Rejected alternatives

- Run Ollama as an unconditional Compose service: rejected because downloading a
  multi-gigabyte model would slow normal startup and CI.
- Permit arbitrary model hostnames: rejected because it would weaken the local-only
  privacy and SSRF boundary.
- Give model output direct settlement authority: rejected because it violates the
  product invariant.

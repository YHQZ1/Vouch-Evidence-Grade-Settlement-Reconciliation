# ADR 0009: Build a review-only evidence-first React interface

**Status:** Accepted  
**Date:** 2026-08-24

## Context

Phase 6 exposes a synchronous, process-local FastAPI boundary with immutable
source uploads, deterministic reconciliation, close readiness, settlement and
exception pages, audit pagination, and canonical exports. Finance operators need
an interface that makes the proof legible without creating a second financial
authority in the browser.

## Decision

Phase 7 uses React, Vite, TypeScript, React Router, TanStack Query, and Tailwind
CSS v4 through `@tailwindcss/vite`. The root stylesheet uses `@import
"tailwindcss"` and CSS-first theme tokens; visual styling is utility-first and
does not retain the former selector stylesheet. The
frontend calls only the Phase 6 API, keeps mutations explicit and non-retrying,
aborts stale reads, and treats all API text as untrusted text. OpenAPI is
snapshotted from the FastAPI app, transformed into `src/types/generated.ts`, and
checked together in a reproducible contract script. The wrapper derives request
and response aliases from generated operations/schemas.

The UI is organized around batch setup, close-readiness overview, settlement
evidence, materiality-ranked exceptions, audit explanation, and server-owned
exports. Money is formatted from integer subunits with visible unsafe-integer
failure. Verified, proposed, and rejected evidence are separate statuses. The
API's process-local limitation is stated in the shell and stale batch IDs show a
recovery state.

Accessibility is part of the feature boundary: semantic landmarks, skip link,
keyboard-visible focus, text plus structure for status, reduced motion, labelled
controls, `aria-live` feedback, and an Escape-closing, focus-trapping audit
drawer. Responsive layouts target 1440×900, 1024×768, and 390×844.

## Consequences

- Reviewers can trace a close decision from exact money buckets to source
  fingerprints, movement-level links, reason codes, and audit events.
- A backend restart remains an honest limitation rather than a blank workspace.
- The client cannot clear exceptions, override policy, post entries, move money,
  invoke AI, or persist source bytes.
- The client carries aliases over a generated TypeScript contract alongside a
  generated OpenAPI snapshot; either artifact becoming stale fails the frontend
  contract check.
- Durable persistence, authentication, tenancy, human resolution, and Phase 8
  AI remain outside the interface.

## Alternatives considered

### Client-side reconciliation

Rejected because it would duplicate financial policy and create a second,
potentially divergent authority.

### A generic dashboard library

Rejected because evidence lineage, proposed-versus-verified status, and exact
money basis require deliberate review surfaces rather than decorative metrics.

### Browser persistence of batches or results

Rejected because the Phase 6 repository is process-local and the frontend must
not create a misleading retention boundary or store uploaded financial bytes.

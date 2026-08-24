# Vouch review interface

Phase 7 is a review-only React interface for the Phase 6 FastAPI batch API. It
does not reconcile, clear exceptions, post journals, move money, invoke AI, or
persist source bytes in the browser. The backend remains the sole authority for
financial decisions.

## Local setup

```bash
cd frontend
npm install
npm run dev
```

In another terminal:

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app
```

Open `http://127.0.0.1:5173`. Vite proxies `/api`, `/healthz`, and
`/openapi.json` to `http://127.0.0.1:8000`; production builds use same-origin
API paths.

## Scripts

| Script | Purpose |
| --- | --- |
| `npm run dev` | Vite development server |
| `npm run build` | Strict TypeScript check and production bundle |
| `npm run lint` | ESLint checks |
| `npm run typecheck` | Strict TypeScript check |
| `npm run test` | Vitest unit/integration tests |
| `npm run api:generate` | Regenerate the OpenAPI snapshot and `src/types/generated.ts` |
| `npm run api:check` | Fail when either generated contract artifact is stale or consumed routes/schemas are missing |
| `npm run e2e` | Playwright against real FastAPI + Vite servers |

`src/types/openapi.json` and `src/types/generated.ts` are generated from
`backend.app.main:app`. `src/types/api.ts` only aliases generated schemas and
operation success responses; hand-written request wrappers therefore cannot
silently diverge from the API document. Run `npm run api:generate` after an
intentional backend contract change, review both generated artifacts, then run
`npm run api:check`. Generated output is not financial authority: the backend
continues to own reconciliation and verification.

The visual system intentionally uses an OS-provided sans-serif and monospace
fallback stack. No remote font CDN or untracked font asset is required, so the
interface remains deterministic and offline-safe.

## Routes and architecture

- `/` — explicit evaluation clock, four independent immutable source uploads,
  upload fingerprints, lifecycle errors, and explicit run action.
- `/batches/:batchId/overview` — policy-derived close readiness, exact integer
  money buckets, source provenance, and ingestion accounting.
- `/batches/:batchId/settlements` — URL-preserved search and filters.
- `/batches/:batchId/settlements/:settlementId` — signed-net arithmetic,
  Razorpay → Bank → Ledger evidence, controls, candidates, exceptions, and
  decision provenance.
- `/batches/:batchId/exceptions` — deterministic materiality-ranked queue.

The code is split into feature modules under `src/features`, shared accessible
controls under `src/components`, server-state/API code under `src/lib`, and API
contracts under `src/types`. TanStack Query owns read caching and abort signals;
mutations do not retry.

## Trust and accessibility decisions

Money is formatted from integer currency subunits with `BigInt`; only semantic
`*_subunits` calculated values become INR, while counts and scores remain in
their original form. Invalid monetary strings fail visibly. Source text is
rendered as text, not HTML. Proposed and rejected evidence always carry explicit
status labels. Every source ID, link ID, journal ID, fingerprint, reason code,
candidate score/signal, and decision citation is reachable in progressive
disclosure and individually copyable. The audit drawer supports Escape, focus
return, focus trapping including initial-container Shift+Tab, keyboard-only
activation, complete bounded pagination, retry/error/empty states, and
cancellation.

The interface includes a skip link, semantic headings/landmarks, labelled
controls, visible focus, `aria-live` upload/run messaging, reduced-motion CSS,
responsive layouts at desktop/tablet/mobile widths, and deliberate loading,
empty, offline, failed-run, incomplete, and backend-restarted states.

The API is process-local by design. A backend restart removes batches, so a stale
deep link shows recovery guidance rather than an empty workspace. The frontend
has no authentication or tenancy boundary and must not be deployed as a
production financial control endpoint without a new architecture decision.

## Demonstration

Use the frozen clock `2026-08-31T18:30:00Z`, upload the four files in
`../data/demonstration/inputs`, run reconciliation, confirm `BLOCKED` readiness
and 12 settlements, inspect the material exceptions, open a settlement audit
explanation, and download an export. The browser never reads ground-truth
labels; all assertions come from API behavior.

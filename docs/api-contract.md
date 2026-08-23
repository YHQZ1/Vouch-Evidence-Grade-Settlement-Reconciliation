# Phase 6 HTTP API contract

The API is a local, synchronous boundary around the deterministic
`ReconciliationService`. It does not expose ground truth, evaluation modules,
raw server paths, or model behavior.

## Lifecycle

`POST /api/v1/batches` creates an `awaiting_sources` batch. The four required
source kinds are `gateway`, `bank`, `ledger`, and `policy`. Uploading all four
transitions the batch to `ready`; a run transitions it to `running` and then to
`completed` or `failed`. Sources are immutable once a run starts. A failed
batch is terminal in this phase.

The evaluation clock is required as an ISO-8601 timestamp with an explicit UTC
offset, for example `2026-08-31T18:30:00Z`. Lifecycle timestamps are
informational UTC metadata and do not affect reconciliation.

## Endpoints

| Method and path | Success | Purpose |
| --- | --- | --- |
| `GET /healthz` | `200` | Existing health contract, unchanged |
| `POST /api/v1/batches` | `201` | Create a batch |
| `PUT /api/v1/batches/{batch_id}/sources/{source_kind}` | `201` new, `200` identical retry | Store one bounded raw source |
| `GET /api/v1/batches/{batch_id}` | `200` | Lifecycle, readiness, fingerprints, and safe failure metadata |
| `POST /api/v1/batches/{batch_id}/reconciliation-runs` | `200` | Run synchronously or return the completed run |
| `GET /api/v1/batches/{batch_id}/result` | `200` | Complete immutable canonical `BatchResult` |
| `GET /api/v1/batches/{batch_id}/settlements` | `200` | Ordered, paginated settlements |
| `GET /api/v1/batches/{batch_id}/settlements/{settlement_id}` | `200` | One settlement |
| `GET /api/v1/batches/{batch_id}/exceptions` | `200` | Ordered, paginated exceptions and useful filters |
| `GET /api/v1/batches/{batch_id}/close-readiness` | `200` | Policy-derived close assessment |
| `GET /api/v1/batches/{batch_id}/audit-events` | `200` | Ordered, paginated append-only audit events |
| `GET /api/v1/batches/{batch_id}/exports/reconciliation-result` | `200` | Canonical JSON result download |
| `GET /api/v1/batches/{batch_id}/exports/exceptions` | `200` | Canonical JSON exception download |
| `GET /api/v1/batches/{batch_id}/exports/audit-events` | `200` | Canonical JSON audit download |

List endpoints use bounded `offset`/`limit` pagination. The default limit is
`min(50, VOUCH_MAX_PAGE_SIZE)` and the maximum is 100 by default. Results are
ordered by settlement ID, exception ID, or audit sequence number. Empty pages
are valid at the exact end boundary.

## Upload contract

Upload raw bytes as the request body, set `Content-Type`, and optionally set
`X-Source-Filename`. CSV sources require `text/csv`; policy requires
`application/json`. The default maximum is 10 MiB per source and is configurable
through `VOUCH_MAX_UPLOAD_BYTES` with a hard ceiling of 100 MiB. Payloads are
SHA-256 fingerprinted and retained byte-for-byte. Client filenames are never
filesystem paths. Fatal malformed files, invalid UTF-8, unsupported headers,
and invalid policy JSON fail at upload; row-level malformed records that Phase
4 intentionally preserves remain rejected evidence and exceptions.

Identical retries require identical bytes, filename, and content type. A
different replacement receives `409 SOURCE_CONFLICT`. Uploads after running,
completion, or failure receive `409 SOURCES_IMMUTABLE`.

## Errors

Every handled error has this shape:

```json
{"error":{"code":"BATCH_NOT_FOUND","message":"batch was not found","details":[]}}
```

Stable codes include:

| Status | Codes |
| --- | --- |
| `404` | `BATCH_NOT_FOUND`, `SETTLEMENT_NOT_FOUND` |
| `409` | `BATCH_INCOMPLETE`, `RUN_ALREADY_IN_PROGRESS`, `INVALID_LIFECYCLE`, `SOURCE_CONFLICT`, `SOURCES_IMMUTABLE`, `RESULT_UNAVAILABLE` |
| `413` | `UPLOAD_TOO_LARGE` |
| `415` | `UNSUPPORTED_CONTENT_TYPE` |
| `422` | `INVALID_REQUEST`, `INVALID_EVALUATION_CLOCK`, `INVALID_FILENAME`, `INVALID_SOURCE`, `UNSUPPORTED_SOURCE_KIND` |

Internal exception text, stack traces, temporary paths, labels, and ground truth
are not returned. JSON exports use sorted keys, compact separators, UTF-8, safe
`Content-Disposition` filenames, integer currency subunits, and stable ordering;
repeated reads are byte-identical.

The reconciliation-result export is the complete `BatchResult` object. The
exception export is `{ "batch_id": "...", "exceptions": [...] }`; the audit
export is `{ "batch_id": "...", "audit_events": [...] }`. These shapes are
also declared in OpenAPI.

## Security and persistence limitations

Phase 6 has no authentication, authorization, tenancy, rate limiting, durable
retention, or production deployment boundary. The process-local repository is
for the local demonstration only; restart loses all batches. The API performs no
money movement or accounting writes, and no credentials or external services
are configured.

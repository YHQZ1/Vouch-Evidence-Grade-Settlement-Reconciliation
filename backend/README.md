# Vouch backend

This package contains the Phase 1 backend foundation, Phase 2 canonical domain
contracts, the Phase 3 synthetic-data boundary, the Phase 4 deterministic
reconciliation engine, and the Phase 5 evaluation-only harness. The domain layer defines
immutable source lineage, raw evidence, integer currency-subunit arithmetic,
gateway/bank/ledger records, policy inputs, and a shared reason-code vocabulary.
The generator lives in `synthetic_data` outside the runtime `app` package and is
not included in the application wheel. Phase 4 reconciliation is in-memory and
has no persistence, AI, or external integrations. Evaluation lives in
`backend/evaluation/` and is not included in the runtime wheel.

## Requirements

- Python 3.12 or newer (Python 3.13 is supported)
- `pip`

## Setup

From this `backend` directory, create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the application and development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]" -c constraints.txt
```

## Run the API

```bash
python -m uvicorn app.main:app --reload
```

The health endpoint is available at <http://127.0.0.1:8000/healthz>.

## Configuration

Settings are read from environment variables prefixed with `VOUCH_`. Safe local
defaults are used when no variables are supplied; the application has no
credentials or data-path settings in this phase.

| Variable             | Default         | Purpose                       |
| -------------------- | --------------- | ----------------------------- |
| `VOUCH_SERVICE_NAME` | `vouch-backend` | Health response service name  |
| `VOUCH_API_VERSION`  | `v1`            | Health response API version   |
| `VOUCH_ENVIRONMENT`  | `development`   | Application environment label |
| `VOUCH_LOG_LEVEL`    | `INFO`          | Application logging level     |

For example:

```bash
VOUCH_LOG_LEVEL=DEBUG python -m uvicorn app.main:app --reload
```

## Quality checks

Run tests:

```bash
python -m pytest
```

Run Ruff linting and formatting checks:

```bash
python -m ruff check .
python -m ruff format --check .
```

AI, persistence, API reconciliation endpoints, and frontend work remain deferred
to later phases. The Phase 4 runtime CLI is:

```bash
python -m app.cli reconcile --help
```

Phase 3 dataset commands are:

```bash
python -m synthetic_data generate --dataset development
python -m synthetic_data generate --dataset demonstration
python -m synthetic_data generate --dataset held-out
python -m synthetic_data verify --all
python -m synthetic_data check-frozen
```

Generation is deterministic and refuses to overwrite existing artifacts unless
`--overwrite` is supplied explicitly. Use `--seed INTEGER` to create a reproducible
variant; the effective seed is recorded in `generation_command`. The public CLI
spelling is `held-out` while its frozen directory is `held_out`. Verification and
frozen checks are read-only. Use `--data-root PATH` to generate into a temporary
location.

Reconciliation results keep gateway-to-ledger evidence at movement granularity:
each link cites one gateway source record and its exact same-journal ledger
assignment. Settlement-level bank/clearing postings use a separate link.

Phase 5 evaluation is run from a clean checkout with:

```bash
python -m evaluation evaluate --dataset held-out --output-dir ../reports/evaluation/held_out
```

The harness saves `runtime-result.json` before loading labels and emits
`metrics.json`, `summary.md`, and `operational.json`. Demonstration evaluation
is supported for development; held-out output is the only accuracy-claim
dataset. Phase 6 APIs, persistence, frontend work, AI, and production
integrations remain excluded.

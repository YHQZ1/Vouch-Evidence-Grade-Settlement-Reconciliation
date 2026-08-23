# Vouch backend

This package contains the Phase 1 backend foundation, Phase 2 canonical domain
contracts, and the Phase 3 synthetic-data boundary. The domain layer defines
immutable source lineage, raw evidence, integer currency-subunit arithmetic,
gateway/bank/ledger records, policy inputs, and a shared reason-code vocabulary.
The generator lives in `synthetic_data` outside the runtime `app` package and is
not included in the application wheel. Reconciliation, persistence, and AI
integration remain deferred to later phases.

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

| Variable | Default | Purpose |
| --- | --- | --- |
| `VOUCH_SERVICE_NAME` | `vouch-backend` | Health response service name |
| `VOUCH_API_VERSION` | `v1` | Health response API version |
| `VOUCH_ENVIRONMENT` | `development` | Application environment label |
| `VOUCH_LOG_LEVEL` | `INFO` | Application logging level |

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

Reconciliation, AI, persistence, and frontend work are deliberately deferred to
later phases. Phase 3 dataset commands are:

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

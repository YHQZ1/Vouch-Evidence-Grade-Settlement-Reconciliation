# Backend boundary

This directory will contain Vouch's reconciliation domain, application services,
persistence adapters, evaluation entry points, and FastAPI delivery layer.

No backend implementation exists yet.

## Planned boundaries

```text
backend/
├── app/
│   ├── api/              # HTTP contracts and route orchestration
│   ├── application/      # Batch and investigation use cases
│   ├── domain/           # Financial entities, policies, and pure controls
│   ├── infrastructure/   # SQLite, files, hashing, and model adapters
│   └── main.py           # Future application composition root
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── property/
│   └── contract/
└── pyproject.toml
```

The exact package tree will be created with the first implementation slice rather
than committed as empty directories.

## Dependency direction

```text
api → application → domain
infrastructure → application/domain interfaces
domain → standard library and explicit value contracts only
```

API routes and SQLAlchemy models must not contain reconciliation logic. The domain
must remain runnable in tests without FastAPI, SQLite, or an AI model.

See the [system architecture](../docs/architecture.md) and
[data contract](../docs/data-contract.md) before adding code.

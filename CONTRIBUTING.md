# Contributing to Vouch

Vouch is currently a focused buildathon project. Contributions should strengthen
the settlement-close loop, its evidence quality, or its measured reliability.

## Before proposing a change

1. Read the [product specification](docs/product-spec.md).
2. Review the [architecture](docs/architecture.md) and accepted
   [architecture decisions](docs/adr/README.md).
3. Confirm that the change is inside the initial scope.
4. Open or update an ADR when the change alters a core invariant, dependency,
   trust boundary, data contract, or deployment assumption.

## Branch and commit conventions

- Branch from `main`.
- Use short, descriptive branch names such as `docs/evaluation-protocol` or
  `feat/settlement-aggregator`.
- Keep commits reviewable and focused on one coherent change.
- Use imperative commit subjects, for example `Define bank input invariants`.

## Definition of done

A product change is complete only when:

- behavior and failure cases are tested;
- deterministic and adversarial fixtures are included where relevant;
- audit-lineage behavior is verified;
- documentation matches the implementation;
- no runtime path can access evaluation ground truth;
- formatting, linting, tests, and evaluation checks pass; and
- no credentials, real merchant records, or machine-local artifacts are added.

## Documentation style

- State decisions and constraints directly.
- Distinguish verified facts from assumptions and proposed behavior.
- Do not publish unmeasured accuracy, throughput, or cost claims.
- Link to primary documentation for external financial or API behavior.
- Prefer small diagrams and examples when they clarify control flow.

## Pull requests

Pull requests should explain the problem, the decision made, the affected trust
boundary, and how the change was verified. Financial behavior changes must name
the corresponding invariant and include a negative test.

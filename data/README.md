# Synthetic data policy

The public Vouch repository will contain synthetic financial data only. Do not add
real Razorpay exports, bank statements, ledger records, credentials, or merchant
identifiers.

## Planned layout

```text
data/
├── fixtures/             # Small readable control-specific cases
├── demo/                 # Frozen 50+ record product walkthrough
├── held_out/             # Frozen evaluation sources without inline labels
├── ground_truth/         # Evaluation-only labels, never runtime imports
└── policies/             # Versioned synthetic close policies
```

Machine-local uploads and run artifacts belong in `data/local/` and `data/runs/`;
both are ignored by Git.

## Dataset requirements

- Generation must be deterministic from an explicit seed.
- Every source row must have a stable identity.
- Money must use integer paise.
- Ledger journals must be independently checked for balance.
- Ground truth must be generated separately from source exports.
- Runtime files must not contain scenario names, expected status, or answer keys.
- Frozen evaluation artifacts must record their generator and schema versions.

See the [canonical data contract](../docs/data-contract.md) and
[evaluation protocol](../docs/evaluation.md).

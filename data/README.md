# Synthetic data policy

The public Vouch repository will contain synthetic financial data only. Do not add
real Razorpay exports, bank statements, ledger records, credentials, or merchant
identifiers.

## Phase 3 layout

```text
data/
├── development/fixtures/ # Small readable control-specific JSON cases
├── development/inputs/   # Generated development source files
├── demonstration/inputs/ # Frozen walkthrough source files
├── held_out/inputs/      # Frozen evaluation source files
├── ground_truth/         # Separate evaluation-only labels
└── manifests/            # Runtime-input hashes and counts only
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

The checked-in seeds are `3101` for development, `3102` for demonstration, and
`3103` for held-out. The fixed evaluation clock is
`2026-08-31T18:30:00Z`. Source-row numbers are one-based data-row numbers and do
not count the CSV header. All generated files are UTF-8 with LF endings.
Generator version `phase3-4.0` records the effective seed in every manifest's
reproduction command. The demonstration and held-out batches each contain 109
gateway rows, 12 settlements, 16 bank rows, and 236 ledger rows.

From `backend/`:

```bash
python -m synthetic_data generate --dataset demonstration --seed 3102
python -m synthetic_data generate --dataset held-out --seed 3103
python -m synthetic_data verify --dataset demonstration
python -m synthetic_data verify --all
python -m synthetic_data check-frozen
```

Ground truth is written only under `data/ground_truth/<dataset>/` after input
file fingerprints and final row numbers are known. Runtime inputs, runtime
manifests, the batch policy, and the application package contain no scenario
IDs, expected states, links, or labels; runtime manifests contain provenance,
source hashes, counts, and the effective reproduction command only. The separate
`data/ground_truth/<dataset>/manifest.json` fingerprints
the answer key. Normal generation cannot overwrite frozen artifacts; changing
them requires an explicit `--overwrite` and a new
review of hashes. Held-out labels are reproducibility artifacts for the future
evaluation harness and must not be used to tune runtime rules or prompts.

See the [canonical data contract](../docs/data-contract.md) and
[evaluation protocol](../docs/evaluation.md).

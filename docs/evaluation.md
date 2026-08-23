# Evaluation protocol

**Status:** Phase 5 complete for deterministic evaluation
**Last reviewed:** 2026-08-24

## Objective

Evaluation must answer two separate questions:

1. How much of the batch can Vouch resolve automatically?
2. How often are those automated resolutions actually correct?

Coverage without correctness is unsafe. Correctness without useful coverage is
not operationally valuable. Vouch reports both and makes false auto-clears visible
in record count and monetary value.

## Dataset separation

### Development fixtures

Small, readable cases used while implementing individual controls. Developers may
inspect their expected outcomes.

### Demonstration batch

A stable 50+ record batch used in the product walkthrough and pitch. It contains
representative clean and exceptional cases but is not the sole source of accuracy
claims.

### Frozen held-out batch

A separately seeded synthetic batch used for the final reported metrics. Rule
thresholds, prompts, and scenario logic must not be tuned by inspecting its labels.

Ground truth remains inaccessible to the runtime engine in all three cases.

Phase 3 locations are `data/demonstration/inputs/`,
`data/held_out/inputs/`, and `data/ground_truth/held_out/`. The runtime-only
manifests in `data/manifests/` contain source hashes and counts but no labels.
The held-out seed is `3103`, with fixed clock `2026-08-31T18:30:00Z`; future
rules and prompts must not be tuned by inspecting its separate answer key.
The current phase freezes evidence and verification and publishes deterministic
evaluation metrics. The generator records `phase3-4.0`, the effective seed, and
the fixed clock in each manifest. `valid_bank_arrival_within_sla` has an exact
credit and is cleared; `pending_within_sla` has no credit and an age below 48
hours; `overdue_missing_bank_credit` has no credit and an age above 48 hours.

## Units of evaluation

Metrics are reported at multiple levels:

- **record link:** whether two source records were linked correctly;
- **settlement:** whether the settlement's evidence and state are correct;
- **exception:** whether a seeded issue was detected and classified correctly;
- **money:** how much value was safely cleared or left unresolved; and
- **batch:** whether the final close-readiness decision is correct.

The report must state its denominator. Raw CSV row count must not be used to
inflate the number of business transactions evaluated.

## Required metrics

### Match rate

```text
cleared eligible items / all eligible items
```

Items classified as `excluded` are not in the denominator. Pending items remain
visible and are reported separately.

### Link precision

```text
correct predicted links / all predicted links
```

This is the primary protection against false relationships.

### Link recall

```text
correct predicted links / all true links
```

### Auto-clear precision

```text
correct automated clear decisions / all automated clear decisions
```

The MVP safety target is 100% on the frozen held-out batch. Results below that
target must be reported honestly rather than hidden behind aggregate accuracy.

### Auto-clear coverage

```text
automatically cleared eligible items / all eligible items
```

### Money-weighted reconciliation rate

```text
verified absolute value / total in-scope absolute value
```

The exact value basis must be named to avoid double-counting payment gross,
settlement net, and ledger lines.

### False-auto-clear value

The sum of absolute monetary value associated with incorrect automated clear
decisions. This is always reported, including when it is zero.

### Exception recall

```text
correctly surfaced seeded material exceptions / all seeded material exceptions
```

### Operational metrics

- total batch runtime;
- deterministic processing runtime;
- optional model runtime;
- records processed per second;
- number and proportion of agent-invoked cases;
- model schema-failure count;
- model abstention count; and
- deterministic-verifier rejection count.

## Status scoring

A result is correct only when both the resolution state and its evidence are
correct. A plausible explanation attached to the wrong records is incorrect.

`pending_within_sla` is evaluated using the batch's frozen clock and settlement
policy. Tests must not depend on the developer's current system time.

## Evaluation procedure

1. Generate or load the frozen source files and ground truth from different paths.
2. Run Vouch with a pinned schema, rule, policy, and prompt version.
3. Save runtime results before loading ground truth.
4. Verify that runtime artifacts contain no ground-truth-only fields.
5. Join results to labels through the evaluation-only adapter.
6. Calculate record, settlement, exception, money, and batch metrics.
7. Emit a machine-readable result and a human-readable summary.
8. Fail the release gate if a false auto-clear or missed blocking exception exists.

## Property and metamorphic tests

In addition to example-based tests, the implementation will verify:

- row order does not change a result;
- input identifiers remain strings under all supported shapes;
- settlement aggregation equals the signed sum of its members;
- adding an unrelated bank row cannot invalidate an existing verified match;
- a bank or ledger record cannot be consumed by incompatible matches;
- a journal remains balanced after canonicalization;
- equivalent timestamp representations produce the same canonical time;
- integer money never passes through a floating-point representation;
- a malformed or injected narration cannot modify tool permissions;
- model failure cannot promote a case; and
- evaluation labels are not importable from runtime modules.

## Reporting rules

- Never publish hand-calculated performance numbers.
- Never report only the best seed or a cherry-picked case.
- Always disclose dataset size, scenario distribution, policy version, model mode,
  and whether AI was available.
- Separate deterministic performance from optional model latency.
- Include the full unresolved exception list.
- Retain evaluation artifacts used for the pitch in the public repository.

## Release gates

Before the submission can claim evaluation readiness:

- all seeded material exceptions are surfaced;
- the held-out batch has zero false auto-clears;
- close readiness matches ground truth;
- every cleared result contains valid lineage;
- the no-model run completes safely;
- one invalid-model-output scenario is demonstrated; and
- reported metrics can be regenerated from a clean checkout.

## Phase 5 implementation contract

The evaluation entry point is outside runtime `app/`:

```bash
cd backend
python -m evaluation evaluate \
  --dataset held-out \
  --output-dir ../reports/evaluation/held_out
```

`demonstration` is supported for development and walkthroughs. Only `held_out`
is eligible for final accuracy claims. The command validates the runtime
manifest and input fingerprints, runs the label-free Phase 4 engine, saves and
validates `runtime-result.json`, loads labels through the evaluation-only
adapter, validates identity and versions, scores, and writes reports. Runtime
output is checked for label-only fields before labels are opened.

The exact Phase 5 denominator and money contracts are:

| Metric | Numerator | Denominator |
| --- | --- | --- |
| Match rate | correct automated clears with valid lineage | labelled `auto_clear_eligibility` settlements |
| Verified link precision | exact verified predicted relationships | unique verified predicted relationships |
| Verified link recall | exact verified predicted relationships | exact expected verified relationships |
| Bank-link precision/recall | exact verified settlement-to-bank source relationship | verified predicted / expected bank relationships |
| Gateway-to-ledger precision/recall | exact verified movement relationship including source IDs and journal | verified predicted / expected movement relationships |
| Auto-clear precision | correct automated clear decisions | all automated clear decisions |
| Auto-clear coverage | automated clears on eligible settlements | eligible settlements |
| Money-weighted reconciliation | correctly cleared absolute settlement-net | total in-scope absolute settlement-net |
| Exception recall | surfaced material blocking labels with an expected reason | seeded material blocking exceptions |
| State accuracy | exact expected state | labelled settlements |
| Close-readiness correctness | matching batch readiness | one labelled batch decision |
| Cleared-result lineage validity | automated clears with exact valid lineage | automated clear decisions |

Both `auto_cleared` and `cleared_with_explanation` are automated clear
decisions and are also reported separately. All money values use the named
basis `settlement_net_absolute_subunits`; gateway gross, ledger lines, and bank
postings are never added to that basis. Every ratio retains integer numerator
and denominator and exposes deterministic decimal and percentage strings. A
zero denominator is emitted as `not_applicable`.

The command emits `runtime-result.json` (canonical Phase 4 output saved before
labels), `metrics.json` (complete deterministic machine report), `summary.md`
(deterministic human report), and `operational.json` (wall-clock measurements,
accepted source-record count, throughput, and explicit disabled/not-applicable
model counters). The human report includes source and settlement counts,
scenario distribution, every metric denominator, a state confusion matrix, the
money breakdown, the complete unresolved exception list, release gates,
limitations, and model mode.

`metrics.json` and `summary.md` contain no current timestamp, duration,
temporary path, or random ID. The harness repeats canonical rendering and fails
the deterministic-report gate if bytes differ. Applicable Phase 5 gates fail
the CLI with a non-zero exit code. AI invalid-output and abstention gates are
reported as `not_applicable`/deferred and do not claim to pass in Phase 5.

Phase 5 does not change Phase 4 rules based on held-out labels and does not add
APIs, persistence, frontend work, AI, production credentials, money movement,
or external integrations.

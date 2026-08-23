# Evaluation protocol

**Status:** Accepted for MVP  
**Last reviewed:** 2026-08-23

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

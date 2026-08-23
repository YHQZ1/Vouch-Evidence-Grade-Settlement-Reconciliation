# Vouch evaluation report

Dataset: `vouch-phase3-held_out` (held_out)
Generator: `phase3-4.0`; seed `3103`
Fixed evaluation clock: `2026-08-31T18:30:00Z`
Schema: `v1`; ground-truth schema: `v1`
Policy: `synthetic-phase3-policy-v1`; rule: `phase4-deterministic-v1`
Accuracy-claim eligible: `true`

## Source and scenario counts

| Source | Rows |
| --- | ---: |
| bank_statement.csv | 16 |
| general_ledger.csv | 234 |
| razorpay_recon.csv | 108 |
| Settlements | 12 |

| Scenario | Count |
| --- | ---: |
| adjustment_movement | 1 |
| amount_date_collision | 1 |
| amount_resemblance_is_not_label | 1 |
| balance_account_isolation | 1 |
| clean_multi_payment_settlement | 1 |
| corrupted_conflicting_utr | 1 |
| duplicate_ledger_line | 1 |
| incorrect_fee_booking | 1 |
| incorrect_tax_booking | 1 |
| later_settlement_refund | 1 |
| missing_ledger_line | 1 |
| missing_settlement_utr | 1 |
| normal_fees_and_tax | 4 |
| overdue_missing_bank_credit | 1 |
| pending_within_sla | 1 |
| same_settlement_refund | 1 |
| transfer_movement | 1 |
| valid_bank_arrival_within_sla | 1 |

## Metric table

| Metric | Numerator / denominator | Percentage |
| --- | ---: | ---: |
| Match rate | 4/4 (100.00%) | 100.00% |
| Exact resolution-state accuracy | 12/12 (100.00%) | 100.00% |
| Auto-clear precision | 4/4 (100.00%) | 100.00% |
| Auto-clear coverage | 4/4 (100.00%) | 100.00% |
| Cleared-result lineage validity | 4/4 (100.00%) | 100.00% |
| Verified-link precision | 112/112 (100.00%) | 100.00% |
| Verified-link recall | 112/116 (96.55%) | 96.55% |
| Bank-link precision | 8/8 (100.00%) | 100.00% |
| Bank-link recall | 8/8 (100.00%) | 100.00% |
| Gateway-to-ledger precision | 104/104 (100.00%) | 100.00% |
| Gateway-to-ledger recall | 104/108 (96.30%) | 96.30% |
| Exception recall | 7/7 (100.00%) | 100.00% |
| Money-weighted reconciliation rate | 1560888/5001101 (31.21%) | 31.21% |

## State confusion matrix

| Expected \ Observed | auto_cleared | cleared_with_explanation | critical_exception | excluded | needs_review | pending_within_sla |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| auto_cleared | 3 | 0 | 0 | 0 | 0 | 0 |
| cleared_with_explanation | 0 | 1 | 0 | 0 | 0 | 0 |
| critical_exception | 0 | 0 | 6 | 0 | 0 | 0 |
| excluded | 0 | 0 | 0 | 0 | 0 | 0 |
| needs_review | 0 | 0 | 0 | 0 | 1 | 0 |
| pending_within_sla | 0 | 0 | 0 | 0 | 0 | 1 |

## Money breakdown

Basis: `settlement_net_absolute_subunits`

| Bucket | Absolute settlement-net subunits |
| --- | ---: |
| Total in scope | 5001101 |
| Strict auto-cleared | 1102538 |
| Explained-cleared | 458350 |
| Pending | 441550 |
| Unresolved | 2998663 |
| False auto-clear | 0 |
| False auto-clear count | 0 |

## Automated clear breakdown

`auto_cleared`: 3; `cleared_with_explanation`: 1

## Unresolved exceptions

- `exc_03fcdee1b825c4fe8b1dd0ad9ff7259eb4d458a5f623fdca222efc0bd9871dba` settlement=`set_3103_p06` reason=`journal_unbalanced` blocking=`true` material=`true` value=`419000`
- `exc_0aa3c45aa9d30bdda3fd3561c846486bfd715419a9f28c803d949a9ceaf49e51` settlement=`set_3103_p06` reason=`ledger_line_missing` blocking=`true` material=`true` value=`419000`
- `exc_171f22f2cc690a067db0109a7357fcf6bc3cb6b36ee237426ee39ac2826d71fd` settlement=`set_3103_p02` reason=`ledger_line_missing` blocking=`true` material=`true` value=`431069`
- `exc_33b30dfa75dbc5f1f555d771487fe36da1bb8ace86179bf75030e988955060d6` settlement=`set_3103_p08` reason=`bank_candidate_ambiguity` blocking=`true` material=`true` value=`425800`
- `exc_3f9628ad187919d945761e4aa76a6a4dd52808e17e58cd1b2a4198ea9329997f` settlement=`set_3103_p07` reason=`utr_missing` blocking=`true` material=`true` value=`474500`
- `exc_4a43d1bf84a8a3965f3ceacc8fe953f4d0d91945a207392d9a29098e26857a96` settlement=`set_3103_p08` reason=`insufficient_uniqueness` blocking=`true` material=`true` value=`425800`
- `exc_4c4e9c2a0ad737615e6484f478503f47e1414e00914c72f40aae5f73c1318c7d` settlement=`set_3103_p01` reason=`ledger_line_missing` blocking=`true` material=`true` value=`493169`
- `exc_5ad520f3063fd8f2d2812659ba94ed25894d3ca1e17c7003c5de33f9120c216d` settlement=`set_3103_p05` reason=`ledger_line_duplicated` blocking=`true` material=`true` value=`393025`
- `exc_631fa67bc3a4c870c3fc77337a9b909a1f69cd47e948ea63c19a30d6885e1cc5` settlement=`malformed_settlement` reason=`malformed_source_record` blocking=`true` material=`false` value=`0`
- `exc_718ee87ab1b2cf73c7eeb8908be1dc621f6c6eb67842e4df75e6eea19cf45c08` settlement=`set_3103_p03` reason=`missing_bank_credit` blocking=`false` material=`true` value=`441550`
- `exc_73397cd2da818f1b48347468903e394f5301818ed6e6332a620a5647b036bc9b` settlement=`set_3103_p08` reason=`utr_conflicting_or_malformed` blocking=`true` material=`true` value=`425800`
- `exc_7ac2d9034d09de7f511f2cfbe7348d7f3cfb741aece44a5468dcbfadfe285f80` settlement=`set_3103_p03` reason=`pending_within_sla` blocking=`false` material=`true` value=`441550`
- `exc_890132926e700d0c8ae52a40992fb43612b1c6515c64e66dea73f9bfac2deb5f` settlement=`set_3103_p05` reason=`journal_unbalanced` blocking=`true` material=`true` value=`393025`
- `exc_94e7919b423ccd7e6065d816a02410678489a73e498bc12ffa8beca700866bf8` settlement=`set_3103_p02` reason=`tax_booking_mismatch` blocking=`true` material=`true` value=`431069`
- `exc_97e1dd14befcaa6f85b930528a73f60801fe004ff0e82c8ca15736b1bd347491` settlement=`set_3103_p07` reason=`insufficient_uniqueness` blocking=`true` material=`true` value=`474500`
- `exc_9c43313eb4d9446ac929bd5772510a9b533ea82b18114bd6f9aeb555f678d429` settlement=`set_3103_p10` reason=`missing_bank_credit` blocking=`true` material=`true` value=`362100`
- `exc_a2c1f5462f09eaae6dee189a564418c556899d6af73eee67a16c525f03710a99` settlement=`set_3103_p05` reason=`duplicate_business_identifier` blocking=`true` material=`false` value=`0`
- `exc_b41232f31a3f4e79600dcf6540e9062a8774201492a4d437c35e69c811d99652` settlement=`set_3103_p02` reason=`ledger_account_role_mismatch` blocking=`true` material=`true` value=`431069`
- `exc_b8abd7e55a2da17c0c84d33ec429f486b0fa2857f54c17cc53b923fb0534dd0c` settlement=`set_3103_p10` reason=`overdue_bank_credit_missing` blocking=`true` material=`true` value=`362100`
- `exc_dd9df533f4dd68c76c8390ac9a3bd644b4c1f196e03a298a7586e0e8a10a17ba` settlement=`set_3103_p01` reason=`ledger_account_role_mismatch` blocking=`true` material=`true` value=`493169`
- `exc_e548afa3e4e2efa6b9802c98acb8abeaf335fe6202c670372a7486b7586cbe66` settlement=`set_3103_p01` reason=`fee_booking_mismatch` blocking=`true` material=`true` value=`493169`
- `exc_f2e7d244cdd81e0f693c7a173ebc14f825cd16a2f9f9c86edb1601f997df535c` settlement=`set_3103_p05` reason=`duplicate_business_identifier` blocking=`true` material=`false` value=`0`

## Release gates

| Gate | Status | Observed | Requirement |
| --- | --- | --- | --- |
| false_auto_clear_count | passed | 0 | must equal 0 |
| false_auto_clear_value | passed | 0 | must equal 0 settlement-net subunits |
| seeded_material_exception_recall | passed | 0 | must miss 0 seeded material blocking exceptions |
| close_readiness | passed | BLOCKED | BLOCKED |
| cleared_result_lineage | passed | 4/4 | every automated clear must have exact valid lineage |
| incompatible_record_reuse | passed | 0 | must equal 0 |
| duplicate_verified_relationship_predictions | passed | 0 | must equal 0 |
| verified_bank_link_precision | passed | 8/8 | all verified bank relationships must be exact |
| verified_gateway_to_ledger_precision | passed | 104/104 | all verified gateway-to-ledger relationships must be exact |
| runtime_ground_truth_fingerprints_and_versions | passed | consistent | dataset, source fingerprints, clock, schema, rule, and policy versions must agree |
| deterministic_reports_reproducible | passed | true | canonical metrics and summary bytes must reproduce |
| ai_invalid_output | not_applicable | not_applicable | deferred to Phase 8 |
| ai_abstention | not_applicable | not_applicable | deferred to Phase 8 |

## Limitations and model mode

Model mode: `disabled`; AI-specific invalid-output and abstention gates are not applicable in Phase 5.
- Deterministic Phase 5 evaluation only; AI invalid-output and abstention gates are deferred to Phase 8.
- Demonstration results are for development and walkthroughs; only held_out is eligible for final accuracy claims.
- Phase 6 APIs, persistence, frontend, production integrations, and money movement remain excluded.

## Safety result

False auto-clears: **0 count and 0 subunits**.
Applicable release gates: **all passed**.

# BD_COMPOSITION_v3

Phase 16 — composition of B/D mixtures by SUPERVISED COMPLETION tokens (assistant_only_loss=True), not raw example counts.

## B attribute mix (share of B's supervised completion tokens)

| source | address | category | certifications | classification_method | employment | ev_battery_relevant | ev_supply_chain_role | industry_group | location | primary_facility_type | primary_oems | processes | product_or_service | services | supplier_or_affiliation_type |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| standalone B | 9.28% | 5.11% | 15.76% | 3.86% | 8.58% | 5.74% | 5.39% | 5.0% | 5.1% | 4.57% | 6.04% | 7.38% | 6.99% | 5.16% | 6.05% |
| B share of BD_full | 9.28% | 5.11% | 15.76% | 3.86% | 8.58% | 5.74% | 5.39% | 5.0% | 5.1% | 4.57% | 6.04% | 7.38% | 6.99% | 5.16% | 6.05% |
| B share of BD_controlled | 9.28% | 5.11% | 15.76% | 3.86% | 8.58% | 5.74% | 5.39% | 5.0% | 5.1% | 4.57% | 6.04% | 7.38% | 6.99% | 5.16% | 6.05% |

BD_full uses all of B unchanged, so its B-mix is identical to standalone B by construction. BD_controlled's B-mix is identical here too because B is the anchor arm (never subsampled) in this run -- reported separately regardless, so a future run where D is the smaller arm doesn't silently reuse a stale identity.

## D operation_family mix (share of D's supervised completion tokens)

| source | filter |
|---|---|
| standalone D | 100.0% |
| D share of BD_full | 100.0% |
| D share of BD_controlled | 100.0% |

Only `filter` survives D's eligibility gate (Phase 13/14 excludes argmax_topk/group_by), so this axis is trivially 100% in every row -- reported anyway, since a future eligibility change should show up here rather than be silently assumed away.

## D join_arity mix (share of D's supervised completion tokens)

| source | 0 | 1 | 2 |
|---|---|---|---|
| standalone D | 39.22% | 15.53% | 45.25% |
| D share of BD_full | 39.22% | 15.53% | 45.25% |
| D share of BD_controlled | 39.21% | 15.5% | 45.28% |

If BD_controlled's join_arity mix drifts from standalone D's, that is a finding about the deterministic example_id-order sampler (README:577-582), reported here rather than hidden inside a single aggregate total.


## D task-kind mix and residual repetition bias

Kinds below are derived from task_id generator prefixes, not operation_family.

| source | child | composition | count | filter | threshold |
|---|---|---|---|---|---|
| standalone D | 15.53% | 45.25% | 9.30% | 29.88% | 0.05% |
| controlled extra copies | 14.70% | 46.25% | 39.05% | 0.00% | 0.00% |
| repeated-D extra copies | 16.30% | 44.96% | 38.74% | 0.00% | 0.00% |

Residual bias is unresolved: within each join-arity stratum, the partial cycle still takes a lexicographic prefix. Count tasks sort before filter tasks, so extra copies are not proportional by task kind. Arity balance does not establish overall sampling balance. This disclosure is not acceptance of the sampling design for final training; joint stratification or another justified ordering remains a release gate.

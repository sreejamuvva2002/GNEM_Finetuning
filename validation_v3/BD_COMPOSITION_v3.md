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
| D share of BD_controlled | 39.23% | 15.54% | 45.24% |

If BD_controlled's join_arity mix drifts from standalone D's, that is a finding about the deterministic example_id-order sampler (README:577-582), reported here rather than hidden inside a single aggregate total.


## D task-kind mix and residual repetition bias

Kinds below are derived from task_id generator prefixes, not operation_family.

| source | child | composition | count | filter | threshold |
|---|---|---|---|---|---|
| standalone D | 15.53% | 45.25% | 9.30% | 29.88% | 0.05% |
| controlled extra copies | 15.66% | 44.99% | 9.28% | 30.07% | 0.00% |
| repeated-D extra copies | 15.58% | 45.24% | 9.17% | 30.01% | 0.00% |

The partial cycle is stratified JOINTLY on (join_arity, task_kind). Arity balance alone did not establish sampling balance: an earlier arity-only sampler gave count tasks 39% of extra copies against a 9% source share and repeated no filter task at all, because ordering inside an arity was a lexicographic prefix and count sorts before filter. Within each stratum the order is now a keyed sha256 digest of the example ID, which is deterministic and reproducible from the artifact but decorrelated from the ID text.

## Joint-stratum token-share deviation

Repetition adds whole examples, so no stratum can land exactly on its proportional token target. Actual deviations and the whole-example overshoot are reported here rather than summarised away.

### BD_controlled

```text
complete cycles retained     1
residual token target        1749
residual tokens allocated    1756
whole-example overshoot      7
within-stratum ordering      sha256 digest of 'bd_v3.2_joint_stratified' + example_id (not lexicographic)
```

| stratum | source token share | extra token share | deviation | extra copies |
|---|---:|---:|---:|---:|
| `structured|0|count` | 9.30% | 9.28% | -0.02% | 7 |
| `structured|0|filter` | 29.88% | 30.07% | +0.19% | 23 |
| `structured|0|threshold` | 0.05% | 0.00% | -0.05% | 0 |
| `structured|1|child` | 15.53% | 15.66% | +0.13% | 8 |
| `structured|2|composition` | 45.25% | 44.99% | -0.26% | 14 |

Repetition adds whole examples, so no stratum lands exactly on its proportional token target; deviations are reported above.

### D_repeat_budgetmatched

```text
complete cycles retained     2
residual token target        3505
residual tokens allocated    3512
whole-example overshoot      7
within-stratum ordering      sha256 digest of 'bd_v3.2_joint_stratified' + example_id (not lexicographic)
```

| stratum | source token share | extra token share | deviation | extra copies |
|---|---:|---:|---:|---:|
| `structured|0|count` | 9.30% | 9.17% | -0.13% | 14 |
| `structured|0|filter` | 29.88% | 30.01% | +0.13% | 45 |
| `structured|0|threshold` | 0.05% | 0.00% | -0.05% | 0 |
| `structured|1|child` | 15.53% | 15.58% | +0.04% | 15 |
| `structured|2|composition` | 45.25% | 45.24% | -0.00% | 28 |

Repetition adds whole examples, so no stratum lands exactly on its proportional token target; deviations are reported above.

A stratum whose proportional target is a fraction of one example receives no extra copy; `threshold` (a single task, 0.05% of D tokens) is the only such stratum here. That is unavoidable whole-example rounding, not a selection preference.

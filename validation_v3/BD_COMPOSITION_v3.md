# BD_COMPOSITION_v3

Phase 16 — composition of B/D mixtures by SUPERVISED COMPLETION tokens (assistant_only_loss=True), not raw example counts.

## B attribute mix (share of B's supervised completion tokens)

| source | address | category | certifications | classification_method | employment | ev_battery_relevant | ev_supply_chain_role | industry_group | location | primary_facility_type | primary_oems | processes | product_or_service | services | supplier_or_affiliation_type |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| standalone B | 11.21% | 6.22% | 10.71% | 4.69% | 5.04% | 6.12% | 5.97% | 6.08% | 6.04% | 5.56% | 5.88% | 7.41% | 7.35% | 5.89% | 5.85% |
| B share of BD_full | 11.21% | 6.22% | 10.71% | 4.69% | 5.04% | 6.12% | 5.97% | 6.08% | 6.04% | 5.56% | 5.88% | 7.41% | 7.35% | 5.89% | 5.85% |
| B share of BD_controlled | 11.21% | 6.22% | 10.71% | 4.69% | 5.04% | 6.12% | 5.97% | 6.08% | 6.04% | 5.56% | 5.88% | 7.41% | 7.35% | 5.89% | 5.85% |

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
| standalone D | 37.49% | 16.28% | 46.23% |
| D share of BD_full | 37.49% | 16.28% | 46.23% |
| D share of BD_controlled | 33.72% | 17.26% | 49.02% |

If BD_controlled's join_arity mix drifts from standalone D's, that is a finding about the deterministic example_id-order sampler (README:577-582), reported here rather than hidden inside a single aggregate total.

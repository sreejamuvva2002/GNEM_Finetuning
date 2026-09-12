# DEV_STRUCTURED_R2_v3

Non-tautological structured development set. The original `dev_structured_v3.jsonl` and every result computed from it are preserved unchanged as historical artifacts.

## Why the original set was replaced

All 51 original items quote their complete gold answer inside the question (*"Which recorded company is named X and has &lt;field&gt; recorded as V?"* with gold `[[X]]`), so both SQL baselines scored 51/51 and the set could not discriminate between arms. It was also the checkpoint-selection eval signal in `train_v3.py`.

## Composition

```text
tasks            120
join_arity       {0: 23, 1: 73, 2: 24}
answer_type      {'set': 96, 'scalar': 24}
multi-company set answers  60 of 96
count answers range        [1, 134]
sha256           416f586d405ee0ae1d622448228fdccb9a6222abe82294c5a6521970045a6027
```

## Development anchoring

Each task's COMBINED predicate is satisfied by at least one held-out development record, and those row IDs are stored in `dev_anchor_row_ids`. Drawing each value from development data separately is NOT sufficient: a conjunction of two dev-observed values can describe only training or test records. An earlier revision of this set contained 14 such tasks; they are now rejected at generation. `matching_record_splits` is descriptive only -- it reports which splits contain a satisfying record and never identifies the anchor.

## Query shapes

The arity-1 `mixed` tasks pair a scalar attribute filter with a record-level child-table join. Both operations appear in training individually; their **conjunction does not appear in the task pool**. These are therefore NEW COMBINATIONS OF FAMILIAR OPERATIONS. That is what makes multi-company development answers available without reproducing a trained query, and it is deliberately not a claim that the combined form is in-distribution for the trained arms -- whether a model generalises to the conjunction is part of what the set measures. Candidates whose gold SQL reproduced a trained query were skipped at generation rather than reworded.

## Gates (all fail-closed assertions in the builder)

- no held-out operation construct in any gold_sql
- held-out {certifications, processes} composition excluded
- no gold cell value appears in its own question
- no company name appears in any company-returning question
- no test-split company named in any question
- no gold_sql / fingerprint / question collision with training, pool, few-shot or probes
- scope train_dev_kb; task_split=dev; misleading split key removed
- every task's COMBINED predicate is satisfied by >=1 development record, whose row IDs are retained in dev_anchor_row_ids

## Examples

- `DEVR2_list_location_0` (arity 0, set): Which companies are recorded with location Albany, Dougherty County? -> 1 row(s)
- `DEVR2_count_location_0` (arity 0, scalar): How many distinct companies are recorded with location Albany, Dougherty County? -> 1 row(s)
- `DEVR2_count_location_1` (arity 0, scalar): How many distinct companies are recorded with location Alpharetta, Forsyth County? -> 1 row(s)
- `DEVR2_comp_services_certifications_12` (arity 2, set): Which companies have both services recorded as Thermal Modeling and certifications recorded as AS9100? -> 1 row(s)
- `DEVR2_comp_services_certifications_13` (arity 2, set): Which companies have both services recorded as Thermal Modeling and certifications recorded as ISO/SAE 21434? -> 1 row(s)

This artifact is development-only. No model inference was performed by this builder, no protected probe was read for scoring, and Q42 approval and the final training release remain outstanding.

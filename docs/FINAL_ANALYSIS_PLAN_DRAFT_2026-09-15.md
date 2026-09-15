# Final analysis plan — review draft, 2026-09-15

Status: proposal only. No release, adjudication, frozen analysis decision or
training candidate is created by this document. Final training remains 0/18.
Derived from the proposed schedule and Phase 41 of
`docs/PHASE_PROTOCOL_REFERENCE.md`; historical protocol requirements remain
visible where the current memory-first objective needs a staging decision.

## Run units and information access

Five primary arms have independent training runs at seeds 61/62/63: B_facts,
C_answers, D_sql, BD_controlled, D_repeat_budgetmatched. A_cpt, BC and BD_full each
have one diagnostic run at seed 61. This is 15 + 3 = 18 runs across eight variants.
No smoke or rehearsal adapter counts toward these runs. Seed labels shared across
arms do not guarantee the same example order or random-number consumption.

Stage 1 implements the user's initial tool-free objective: compare every arm
with the same unchanged base on memory-only questions and frozen answer contracts.
D-family training targets are SQL; measuring those models under a direct-answer
contract is a transfer test, not their native SQL task. Report that distinction.
Do not execute a model's SQL to rescue a memory-only answer.

Stage 2, if included in the final released evaluation plan, separately reports
oracle-record and SQL-execution conditions. These are different information-access
conditions. Neither SQL ceiling nor oracle context performance establishes
closed-book competence. Do not mix their scores into a memory-only headline.

## Existing six predeclared protocol contrasts

| ID | Arm | Comparator | Domain / information access | Interpretation |
|---|---|---|---|---|
| P1 | B_facts | base | Factual, memory | Learned factual answering |
| P2 | B_facts | base_ctx_oracle | Factual, different evidence access | Context reference, not an isolated fine-tuning effect |
| P3 | C_answers | base | Structured direct answer, memory | Direct-answer learning |
| P4 | D_sql | base_sql | Structured SQL execution | SQL-generation learning under matched access |
| P5 | D_sql | base_sql_5shot | Structured SQL execution | Relative to prompted SQL baseline |
| P6 | BD_controlled | D_repeat_budgetmatched | Same released evaluation mode and item set | Allocation of supervision at approximately matched token budget |

A_cpt, BC and BD_full remain diagnostic. Additional memory-only contrasts against
base for the other arms should be reported descriptively unless explicitly added
to a frozen confirmatory family before final outputs are inspected. P6's exact
mode and endpoint must be fixed before release; duplicating it across several
endpoints expands the comparison family rather than creating free extra tests.
The controlled versus repeated-D token totals are close, not numerically identical;
report observed exposure and compute alongside the planned budget.

## Endpoints and reporting

Keep probe families separate. Do not average factual, structured, analytical and
general-capability tasks into a universal score with arbitrary weights.
For each run and probe family report numerator/denominator, semantic accuracy,
strict accuracy and format compliance separately. Retain invalid/missing/truncated
answers in the denominator. Report omissions separately from unsupported claims.
For multipart: whole-question all-parts accuracy and per-part accuracy, stratified
by part count and task type. For lists: completeness and extra-member errors.
For uncertainty: pair ambiguous items with answerable controls and report both
clarification success and unnecessary abstention. Analytical tasks require human
rubrics fixed before inference; regex compliance is not semantic scoring.

For each primary arm give all three seed scores, mean and sample SD, plus each
seed's difference from the same fixed baseline. The base has one greedy result,
not three independent baseline runs or an invented SD. A single-seed trained arm
has undefined training-seed SD; deterministic decoding does not remove training
variability that was never replicated.

Preserve knowledge-exposure, entity-dependence, attribute, operation, holdout-axis
and seed strata. Apply split-group weighting only to entity-attributable tasks:
mean within split group, then unweighted mean across groups. Global aggregates
have no group-weighted score. Report both group and item counts.

Q42 all-item reporting is descriptive. Primary-eligible membership and reconciled
golds remain pending Q42 review; do not automatically promote the recorded nine
primary-eligible proposals or the other 33 diagnostic proposals to approved labels.
Additional benchmarks retain separate versions and denominators.

## Uncertainty and multiplicity

The existing protocol calls for paired item-level bootstrap estimates and secondary
McNemar tests on predeclared binary comparisons. These describe uncertainty across
benchmark items conditional on the fitted models, not variability across independent
training runs. Repeated paraphrases, multipart components and shared-company items
are correlated. Report the item-bootstrap limitation and propose a separate
split-group/pair-cluster sensitivity analysis where those clusters are defined;
do not silently replace the historical procedure or invent clusters for global
aggregate queries. Resampling units, counts and random seed must be frozen.

Do not pool three model seeds times N questions as 3N independent training runs.
For P6 show all same-label seed differences, while stating that pairing by seed
label alone does not establish common-random-number variance reduction. Report
arm-wise scores as well. If inferential paired-seed testing is proposed, justify
exchangeability and the seed pairing before interpreting the result.

At three seed pairs, an exhaustive two-sided sign-flip test has only 2^3 sign
assignments. Even a unique maximum absolute effect has its opposite-sign partner,
so its smallest attainable two-sided p-value is 2/8 = 0.25. This does not apply to
item-level McNemar p-values, which address a different unit of analysis. Small
item-level p-values cannot fix the lack of independent training replication.

Apply Holm adjustment to the explicitly frozen family of primary p-values, as
required by the protocol. The six contrast labels alone do not define that family:
multiple probes, strata or per-seed tests multiply its members. Before release,
list every test's contrast, endpoint, eligible item IDs and seed aggregation rule.
Do not select the best seed or smallest p-value after seeing outcomes. If a valid
family is not fixed, retain descriptive effect estimates without confirmatory
significance claims. Undefined standardized effects (zero sample variance) remain
null with raw differences shown, not zero or infinity.

## Failure handling and forgetting

Report attempted/completed/failed runs against the fixed 18-run schedule. Preserve
failed attempts and their logs. An infrastructure retry uses the same declared
variant/seed and documented configuration; outcome-driven hyperparameter changes
create a new experiment version. Never silently omit a weak or failed seed.
Missing prediction records must be represented explicitly by the evaluation
contract rather than dropped. Training/infrastructure failure is reported as such,
not automatically treated as a model answer scoring zero.

Matched general-capability items, prompts and scoring must be fixed before final
model outputs. The current 30-item sanity screen alone cannot support a claim of
no forgetting. Report domain gains alongside general-capability losses and the
limits of whichever broader battery is eventually selected.

## Decisions required before freezing

1. Confirm memory-first reporting and the later scope of oracle/SQL conditions.
2. Fix P6 mode, each primary endpoint and the complete multiplicity family.
3. Fix item/cluster uncertainty procedures and their interpretation limits.
4. Complete Q42 review when requested and select a broader forgetting battery.
5. Review non-executable task rubrics, reviewers and baseline collection plan.
6. Bind the final plan and actual per-run specs to the later release evidence.

No protected outputs were inspected to write this proposal.

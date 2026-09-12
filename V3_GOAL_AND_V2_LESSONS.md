# V3 goal and verified V2 lessons

Written 2026-09-11. This is a portable project handoff and proposed acceptance contract, not an amendment to the frozen experimental protocol. Carry this file and the linked audit evidence into the separate V3 repository. Review the work already present there before changing it.

## Goal

Build and rigorously evaluate a reproducible EV supply-chain assistant that understands company identities and domain terminology, answers factual and multi-condition questions, and correctly completes every requested part of compound aggregate questions over a verified knowledge base. Use fine-tuning to improve interpretation, domain language, tool use, and grounded responses; use authoritative structured data and executable queries for exact facts and calculations. Demonstrate its value against strong untuned baselines on independent evaluations, with traceable evidence and explicit handling of uncertainty.

“Perfect V3” means a carefully specified, auditable process with measured capabilities and limitations. It is not a promise of error-free answers to every possible question. Successful optimization and low training loss alone do not satisfy this goal.

## Evidence to preserve from V2

Primary evidence: [independent training audit](review_training_2026-09-11/REPORT.md), its raw logs, scripts, CSVs, mask reconstructions and AUDIT_MANIFEST.json. Broader findings: [repository review](REPOSITORY_REVIEW_2026-09-11.md). Historical reference: `v2-frozen-reference`, commit `b18313ae593995e8d415880603b3d355dd695ebd`.

- The main completed V2 runs have credible evidence of actual optimization. Original whole-run training losses were A 1.642, B 0.3769, C 0.5717, D 0.02215, BC 0.3979, BD 0.2207. These objectives and target distributions differ; the losses are not a quality leaderboard.
- D's final periodic loss of 0.00001075 and teacher-forced token accuracy of 100% do not establish correct complete answers or generalization.
- No evaluation loss was present in any of the 71 historical training logs. The trainer supplied no evaluation dataset. Optimal stopping and generalization cannot be established from those logs alone.
- The reconstructed V2 dose pipeline dropped all 25 appended examples in each dose arm: after 1,024-token keep-start truncation, those examples had no supervised assistant tokens. All three arms retained the same 647 input/label examples as D. Logs support that reconstruction. The intended 0/5/25-exposure comparison is invalid until rerun correctly; this does not invalidate every V2 result.
- The archived standalone B file has three malformed JSON lines. Its actual logged training file was recovered byte-for-byte from the B prefixes of BC and BD and matched the recorded training hash. This is an archival failure, not evidence that the malformed file was trained.
- Original checkpoint tensors and optimizer states were unavailable for independent replay. Some runs recorded dirty working trees. Preserve exact source, data, environment, and weights in V3.

## Data and answer requirements

1. **Resolve identity before teaching facts.** The inspected workbook contains 205 records and 193 exact trimmed company names; neither count establishes the number of distinct legal entities or sites. The existing 186 split groups serve leakage control. Define stable company/site IDs, aliases, record provenance, conflict handling, and the distinction between company counts and record counts. Normalize labels such as OEM Footprint / OEM (Footprint) without merging unrelated companies that share categories, processes, or services.
2. **Retain useful numeric data with scope.** Employment is already retained in this V3 checkout. Numbers can be represented and learned, but exact filtering and arithmetic should execute against data. Resolve conflicting employment values and document site/global scope, dates, and sources before presenting totals or comparisons. Do not sum ambiguous rows or use SUM(DISTINCT employment) as an identity fix. Latitude/longitude are absent from this checkout's intended scope; restoring them for distance queries requires a documented scope decision, valid site coordinates, and deterministic geographic calculations.
3. **Use the existing process, service, and certification integration.** These fields are already represented in the inspected V3 data and training artifacts. Audit their coverage, terminology, company/site relationships, sources, dates, and uncertainty. Distinguish certifications from standards, registrations, ratings, and compliance claims. “None identified after search” does not prove absence.
4. **Complete compound requests.** Support combinations of filters, distinct-company counts, grouping, rankings, and appropriately scoped sums/averages/minima/maxima. Decompose questions into required outputs, execute each calculation, and check that the final response covers every part. Example: “For companies providing machining and holding a specified certification, give the company count by state, the top three states, and average site employment where comparable data is available.” Define tie rules, missing-value behavior, denominator, units, and entity scope.
5. **Ground explanations and uncertainty.** Return traceable supporting records or document references. Ask for clarification when ambiguity changes the result; distinguish unknown, absent, conflicting, and zero. Broader EV-domain expertise requires a vetted technical knowledge collection and suitable evaluations beyond these company records.

## Keep the research experiment and the intended product explicit

The inspected checkout already contains partial V3 work. Its frozen research design intentionally withholds some operations/compositions from training to measure generalization. The current D training set does not cover the full desired product capability: COUNT is present, but grouping, ranking, SUM/AVG and multipart tool-result conversations are absent.

Preserve the frozen comparison and its held-out conditions unless a decision explicitly amends it. A product training recipe that adds these capabilities should be separately versioned and evaluated. Do not silently add held-out operations to research training or interpret their absence as an accidental implementation defect. Do not combine held-out-company fact memorization tests with database-backed access tests without declaring what information each system can access.

## Work order and acceptance gates

### 1. Reconcile the existing V3 repository

Inventory the separate repository's actual code, data, phase status, decisions, and completed checks. Map existing work to these findings; preserve valid work. Reconcile contradictory phase markers before advancing. Treat prior review handoffs as plans until their implementations and checks are verified.

Close the existing review findings: actual SQL JOIN structure versus metadata and schema guidance; SQL-derived eligibility checks rather than trusting metadata; exact task-ID and source-hash manifests; incorrect repeated-D source mappings; validation of every message; controlled-mixture company coverage and budget provenance; semantic versus alias/schema grading; actual SQL timeouts; and statistical edge cases. See the repository review for precise evidence and scope.

### 2. Freeze a trustworthy data and evaluation contract

Specify entity/site semantics, authoritative fields, treatment of conflicts and missing data, task families, permitted information access, split rules, and baseline configurations. Verify gold answers using independent computations. Define a dedicated development set and protected final test set, including similar names, conflicting records, empty results, numeric conditions, unseen phrasings, and compound requests.

Set numeric quality targets and acceptable regression limits before seeing results. Include complete-answer accuracy, per-part correctness, entity resolution, SQL execution correctness, unsupported claims, and uncertainty handling. Report latency and resource costs where relevant. Set membership and numeric tolerances must have explicit rules; exact SQL string matching must not substitute for semantic correctness.

### 3. Prove what reaches the loss before spending on full training

Parse every artifact; verify manifests and split isolation. Render with the exact pinned tokenizer/chat template, tokenize, construct actual labels, apply the real truncation/packing/filtering path, and inspect retained examples. Record raw, retained, dropped, truncated, and supervised-token counts by arm and task family. Require zero unexplained drops or truncations and nonzero supervised tokens for every intended supervised example. Verify intended exposures and budget comparisons after preprocessing, not only in JSONL.

Run a small smoke training job and inference check. Verify gradients and parameter updates, template compatibility, generation termination, checkpoint reload, and the expected step/token accounting. Pin model revision in the load call, not only in output metadata.

### 4. Train and compare reproducibly

Run the agreed untuned baselines with equivalent data/tool access first. Follow the approved independent-start arm/seed plan; do not chain adapters between comparison arms. Log training and development loss with their masking/aggregation definitions, task-level development results, learning rate, gradients, token counts, runtime, and memory. Use a declared checkpoint-selection rule; retain every adapter used in reported comparisons.

Archive exact source state including any patch, dependency versions, seeds, model/tokenizer revisions, data hashes, full configuration, raw logs, evaluation outputs, checkpoints and replay instructions. Loss is a diagnostic; select and judge systems using the declared evaluation procedure.

### 5. Evaluate the complete assistant and document the decision

Evaluate question interpretation, tool execution, and final answer together. Check every requested sub-answer, numeric result, company set, source, and uncertainty statement. Compare against baselines and report seed variability and failure categories. Keep research generalization results separate from product capability results.

Use the protected final test only after model and procedure selection; if its findings guide further development, use a new protected test for the next final claim. Deliver reproducible results and known limitations, including negative results. If fine-tuning does not provide measurable value over the baseline, record that outcome rather than assuming tuning must be deployed.

## Immediate milestone

Before a full V3 run: verify the existing separate repository against the open review findings, finalize data/identity semantics and evaluation rules, and produce a passing preprocessing exposure report plus a reloadable smoke-run checkpoint. This is the next milestone; choosing more epochs or a larger model comes after it.

## How to reuse this handoff

Keep this document with the V3 repository and copy the linked evidence folder/review so the relative links remain usable. Start future sessions with:

> Read V3_GOAL_AND_V2_LESSONS.md and its audit references, inspect the V3 work already completed, and continue from the first unmet acceptance gate. Preserve the verified V2 lessons and the approved experimental scope. Do not infer correctness from low loss or assume raw examples survived preprocessing.

This file supplies durable project context. Cross-session assistant memory should not be the only record of these findings.

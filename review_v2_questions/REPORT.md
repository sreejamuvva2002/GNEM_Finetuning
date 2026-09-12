# V2 question-by-question answer audit

**Verdict:** V2 contains genuine factual-recall and query-reasoning failures, important scoring errors, and a verified preprocessing failure in the dose experiment. The evidence does not justify attributing everything to a broken model, company-name punctuation, too few epochs, or insufficient model size. Some apparently failed answers are correct; some apparently correct answers contain unsupported facts.

## Scope and how to inspect individual questions

I processed **all 400 archived V2 prediction JSONL files: 78,550 response records**, covering 15 original conditions and seven conditions in each of five seed directories. Every condition has eight probe files. The six principal original fine-tuning variants are aligned over **1,571 questions**.

- [Six-variant comparison CSV](six_variant_comparison.csv): one row per original question, with the actual answer, raw completion, stored score and exact matching training targets for each principal variant.
- [All questions CSV](all_questions.csv): every archived response, including baselines, dose arms and seed runs; filter by condition, probe, source line, attribute, split or triage tag.
- [Full original records plus analysis](all_predictions.jsonl): complete retained item, gold, completion, rendered answer and original scores. No generated answer was truncated in these exports.
- [Verified examples](verified_examples.json): selected cases checked against archived training data, historical database and grading rules.
- [Input manifest](INPUT_MANIFEST.json): exact Git reference, training hashes and all prediction-file hashes. Standalone B uses the previously recovered exact training bytes, not its malformed archived copy.

Reference: `v2-frozen-reference` = `b18313ae593995e8d415880603b3d355dd695ebd`. This is an exhaustive machine-assisted record census plus close inspection of selected failure classes, **not a claim that 78,550 open-ended answers received independent human semantic adjudication**. The CSV triage flags identify evidence for review; they are not automatic causal explanations. Absence of an exact matching QA does not establish absence of all relevant information in passages, related facts, prompts or pretraining.

Original and seed13 runs are reported separately, not treated as independent replicates. Historical scores remain labelled as such; they were not silently replaced by a new universal grade. SQL/routed answers may include external database execution, so their recall scores do not measure knowledge stored in weights. No V3 training data or protocol was changed by this audit.

## 1. The original variants: what their stored scores actually show

The following uses **only probe_recall for original runs**, without combining its paraphrases or certification probe. “Seen companies” is the archived heldin designation. For B/BC/BD, all 321 heldin recall questions match explicit factual training questions; A uses passages, C/D use different objectives.

| Condition | Answer mechanism | Seen-company recall | Held-out-company recall |
|---|---|---:|---:|
| Base | Direct, unchanged model | 47/321 = 14.6% | 9/79 = 11.4% |
| A_cpt | Direct, passage tuning | 90/321 = 28.0% | 16/79 = 20.3% |
| B_facts | Direct, factual QA tuning | 156/321 = 48.6% | 33/79 = 41.8% |
| C_answers | Direct, structured-answer tuning | 41/321 = 12.8% | 8/79 = 10.1% |
| BC_facts_answers | Direct, factual + structured-answer tuning | 163/321 = 50.8% | 32/79 = 40.5% |
| D_sql | Generated SQL, database-derived answer | 272/321 = 84.7% | 74/79 = 93.7% |
| BD_facts_sql | Mixed tuning, SQL/database inference here | 271/321 = 84.4% | 74/79 = 93.7% |

These are the archived grader's rates, not newly certified semantic accuracies. The scoring defects below matter. Nevertheless, B's 165 stored failures among the 321 exactly trained questions demonstrate that correct training targets did not yield reliable free-generation recall.

Original B factual recall on training-company questions varies strongly by attribute:

| Attribute | Stored correct / questions |
|---|---:|
| Primary OEMs | 31/32 |
| Primary facility type | 40/45 |
| EV supply-chain role | 19/26 |
| EV/battery relevance | 20/39 |
| Category | 14/30 |
| Industry group | 14/33 |
| Location | 15/39 |
| Employment | 2/35 |
| Product/service | 1/42 |

The factual variant was much better at some repeated categorical values than at entity-specific product descriptions and employment. This supports a limited conclusion about these tasks and this recipe. It does not prove that all categorical answers were memorized, that correct descriptions absent from a string match must be wrong, or that LLMs cannot learn numbers.

B's seen-company recall across five independently recorded seed runs is 156, 158, 149, 160 and 170 correct out of 321 (seeds 13, 29, 47, 61, 79). The problem is not confined to one unlucky run. The modest original BC improvement is not a multi-seed causal proof that combining objectives fixes factual recall; no five-seed BC comparison is present.

## 2. Exact question examples and what each establishes

### A. Correct fact trained, wrong answer generated; paraphrase succeeds

**Question:** What supply chain tier/category is ACM Georgia LLC classified under?

**B training target:** ACM Georgia LLC is classified as Tier 2/3.

**Actual B answer:** ACM Georgia LLC is classified as Tier 1.

**Archived database:** Tier 2/3. This exact question and target are present in recovered B training data. The company is heldin.

For the paraphrase **“Which tier is ACM Georgia LLC assigned to in the Georgia EV supply chain?”**, the same original B condition answers **“ACM Georgia LLC is assigned to Tier 2/3 in the Georgia EV supply chain.”**

**Supported diagnosis:** genuine factual error on the original prompt, with wording-sensitive behavior. It is incorrect to conclude from the first answer that the model never learned the fact. There is no evidence here that a specific other company's identity caused the error.

Across the 400 paired original/paraphrased recall items, original B's stored correctness changes on 63: 17 wrong-to-right and 46 right-to-wrong. These flips are an operational robustness diagnostic, subject to the underlying grader's limitations. [All disagreement records](paraphrase_disagreements.json).

### B. Numeric fact trained, wrong number generated

**Question:** How many people does Adient employ?

**Training target and archived database:** 180.

| Condition | Actual answer |
|---|---|
| B_facts | Adient employs 100. |
| BC_facts_answers | Adient employs 130. |
| D_sql | 180, after executing `SELECT employment FROM companies WHERE company = 'Adient' LIMIT 1;` |
| BD_facts_sql | 180, after executing `SELECT employment FROM companies WHERE company = 'Adient';` |

B and BC both contain the exact question with target “Adient employs 180.” This is a genuine observed numeric recall failure, not a held-out-company issue. The SQL conditions succeed through lookup; that does not demonstrate memorization. The value is verified against the historical dataset, not asserted as Adient's current real-world total employment.

### C. Extra certifications invented relative to the dataset, but graded correct

**Question:** Which certification standards does ADVICS Manufacturing Georgia LLC hold?

**Training target / archived gold / historical certification table:** ISO 9001.

**Actual B answer:** ADVICS Manufacturing Georgia LLC holds: IATF 16949; ISO 14001; ISO 27001; ISO 45001; ISO 9001.

**Stored score:** correct = 1.0.

**Supported diagnosis:** the response added four credentials unsupported by the benchmark evidence. The grader's `value_match` accepted the answer because the expected value appeared. This is both an answer-faithfulness failure and an overgenerous metric. It does not establish whether any extra credential exists outside the archived dataset.

All 118 original B certification outputs follow its company-holds template and were parsed for a literal-set check. Stored correctness is 68/118; exact set agreement after case/whitespace normalization is 15/118. The remaining 53 stored passes contain extra entries. This strict audit does not apply semantic synonym resolution; it must not be presented as independently verified real-world certification accuracy. [Every certification comparison](certification_literal_set_audit.json).

### D. Correct answer marked wrong because the scorer required an unasked number

**Question:** Which county have the highest total Employment among Tier 1 suppliers only?

**Actual C answer:** There is 1 matching county:
- Troup County

**Actual BD answer after SQL:** Troup County.

**Stored score:** 0.0 for each.

**Independent historical-DB calculation:** Troup County, recorded sum 2,435.

`taxonomy.py` requires both the phrase “Troup County” and the number 2435 for question 8. The question asks which county; it does not explicitly ask to state the total. The county answers are correct to that requested output. The stored zero is an overstrict scoring-contract failure, not a wrong county prediction. Report any revised question-aligned score separately rather than overwriting historical results.

D_sql also receives zero on this question, but for a different reason: it generates `WHERE supplier_or_affiliation_type = 'Tier 1'` instead of filtering `category`. That is a real field-selection error. Same stored score, different cause.

### E. Semantic product request reduced to exact text equality

**Question:** Find Georgia-based companies that manufacture copper foil or electrodeposited materials suitable for EV battery current collectors.

**Actual D SQL:**

```sql
SELECT DISTINCT company FROM companies
WHERE product_service = 'Copper foil'
   OR product_service = 'Electrodeposited materials'
ORDER BY company;
```

**Actual result:** no matches.

**Recorded matching source entry:** Duckyang — “High-quality electrodeposited (ED) copper foil for electric vehicles.” The archived database confirms that text.

**Supported diagnosis:** a natural-language capability description was mapped to exact equality against fragments that are not full stored values. The database is doing what the query requests; query interpretation fails. More literal factual QA alone does not directly train semantic product matching. V3 needs reviewed vocabulary/relationship handling and appropriate tasks within its predeclared operation policy.

### F. Compound filtering and requested columns mishandled

**Question:** List all Tier 2/3 companies in Georgia with primary involvement in the electric vehicle or battery supply chain and specify their respective roles.

**Actual BD SQL:**

```sql
SELECT DISTINCT company FROM companies
WHERE category = 'Tier 2/3'
  AND ev_supply_chain_role LIKE '%EV%'
   OR ev_supply_chain_role LIKE '%Battery%'
ORDER BY company;
```

**Supported defects:** AND binds before OR, so battery-role matches are not constrained to Tier 2/3. The output also omits the requested role column. The selected predicates themselves are only a heuristic for “primary involvement.” Correct parentheses alone would not establish a correct business interpretation.

The archived answer lists six companies; the benchmark gold names Duckyang, GSC Steel Stamping LLC and Enchem America Inc. Treat that gold as the historical task interpretation, not proof of universal product eligibility.

B's answer to this same question repeats “Kia North America Inc.” 77 times and ends partway through another numbered item. This is observed repetitive/incomplete generation. The record does not retain sufficient finish-reason evidence to certify the precise stopping cause; do not automatically call it a proven token-limit event.

### G. Invalid SQL on a supplier-concentration question

**Question:** Which EV Supply Chain Roles in Georgia are served by only a single company, creating a single-point-of-failure risk for the state's EV ecosystem?

**Actual BD SQL:**

```sql
SELECT DISTINCT ev_supply_chain_role FROM companies
WHERE COUNT(DISTINCT company) OVER
      (PARTITION BY ev_supply_chain_role) = 1
ORDER BY ev_supply_chain_role;
```

**Actual and independently reproduced error:** `DISTINCT is not supported for window functions`.

A query expressing the role/company-count condition would group by role and use `HAVING COUNT(DISTINCT company) = 1`, with company identities included if the answer requires them. Even a correct query only establishes concentration in the recorded dataset; a single source entry does not alone establish an actual statewide supply risk.

### H. Held-out company facts guessed confidently

**Question:** Where in Georgia is Ajin Georgia located?

**Actual B answer:** Ajin Georgia is located in Covington, Henry County.

**Archived source:** Register, Bulloch County.

This item is labelled heldout, and neither its exact question nor its company/attribute pair is in B training. This is not evidence of forgetting a trained cell. The operational failure is giving an unsupported confident answer rather than signalling uncertainty. Correct answers to other held-out categorical questions can result from prior knowledge or common-value predictions; they cannot automatically be called learned factual recall.

## 3. Training problem, model problem, or evaluation problem?

| Finding | Evidence strength | What to do |
|---|---|---|
| Exact B training targets do not reliably emerge during generation | Directly observed in predictions and matched training records | Measure generated-answer performance on known training questions and independent paraphrases; examine failures by attribute. |
| Some answers vary with wording | Direct paired prediction evidence | Test aliases/paraphrases and entity contrasts; keep analytical task families separated across splits. |
| B teaches factual answers, C teaches template answers; neither alone covers all analyst requests | Training-content and output evidence | Respect variant objectives; broaden task coverage only through declared designs. Do not assume one-sentence fact QA teaches multipart analysis. |
| Semantic grounding, field selection, logical constraints and query syntax fail separately | Inspected SQL and database execution | Use distinct diagnostic categories and targeted regression tasks. |
| Grading overcredits extra credentials and undercredits some correct county answers | Grader code plus actual predictions | Validate graders against known good/bad answers, require all and only supported set entries, and score requested parts rather than unasked details. |
| V2 dose examples were dropped after truncation | Prior source/mask reconstruction supported by logs | Verify real post-preprocessing exposure. The intended dose comparison is invalid; it does not invalidate all original main runs. |
| B archive malformed, actual training bytes recoverable | Prior log hashes and byte-identical recovery | Archive exact runtime data and verify it before and after training. Do not claim the malformed archive was used for the successful run. |
| More epochs, different LR/rank or larger model would solve this | Not established | Test through controlled development experiments, not guess from a low loss or one wrong answer. |

The main V2 runs did optimize: their logged losses fell. Original B whole-run train_loss was 0.3769; last periodic loss 0.1658. D's last periodic loss was 0.00001075. These predict supervised training tokens under teacher forcing, not whether a freely generated answer is complete, faithful and correctly reasoned. Repeated answer phrasing and easy tokens can coexist with errors on critical factual tokens. Quantifying that mechanism for a particular answer requires teacher-forced per-token likelihoods and a checkpoint replay, which this archive cannot currently provide.

There was no eval_loss in the 71 historical training logs, and original checkpoint tensors were unavailable for replay. Consequently, undertraining, overfitting, particular update effects and optimal stopping are not independently established. Increasing epochs blindly could improve or worsen the desired behavior. [Historical training audit](../review_training_2026-09-11/REPORT.md).

No evidence here proves that `OEM Footprint` punctuation caused the ACM error. No evidence proves the model architecture is inherently incapable of company recall. The supported conclusion is that this training/evaluation system did not achieve reliable company-specific and analyst-question performance, and its metrics sometimes obscured that fact.

## 4. Consequences for the active V3 experiment

Keep the user's eight-variant comparison. Preserve full process/service/certification information under the current amendment, with Certification Count remaining the explicit training exception. Complete source inclusion is necessary for coverage but is not sufficient for accurate recall or reasoning.

Before final training:

1. Fix scoring contracts first: extra facts, missing answer parts, legitimate paraphrases, correct minimal answers, invalid output and real execution errors need distinct tests.
2. Verify actual training exposure and labels, not only source JSONL counts. Protect complete lists, critical numeric targets and output endings from unintended truncation.
3. Trace every example to its source and scope. Explain conflicting observations and unknowns rather than inventing site-level truth.
4. Build task-family development diagnostics: factual identity, numbers, credential-set precision/recall, semantic field grounding, filter logic, aggregates, multipart completeness and abstention. Keep operation/composition holdouts faithful to the active protocol.
5. Compare variants using common task scores and stated information access. SQL lookup success must not be presented as model-only memorization.
6. Log train/dev loss, generated answers and seed variability; retain checkpoints. Select on development evidence and keep final tests protected.

The concrete issue is a combination: incomplete/unstable factual generation, mismatch between training tasks and analyst requests, SQL interpretation failures, misleading grading, and specific pipeline defects. The remedy is to measure and correct these separately, not label every failure as “the LLM forgot” or assume one larger training run will fix them all.

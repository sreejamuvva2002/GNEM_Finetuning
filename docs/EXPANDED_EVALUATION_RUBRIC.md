# Expanded development evaluation — proposed rubric

Status: design draft for review, not approved golds or training targets. Preserve the original operation/composition holdouts. New questions and results must have separate versioned inputs and baselines. Q42 remains a distinct pending business benchmark.

## Three separately reported tracks

1. Memory: training-company facts and combinations using allowed operations. No source context or external execution supplied. Report unseen-company questions separately; correct unknown responses must not be confused with failure to recall trained facts.
2. Provided evidence: give all compared models the same bounded, source-attributed company records. Tests interpretation of evidence, not weight memorization. Record context hashes and scope. Do not derive context from gold answers.
3. Clarification/insufficient evidence: determine whether information needed for a requested conclusion is absent or ambiguous. A question may require both supported partial answers and an explicit limitation. Do not reward blanket refusal when the supplied evidence supports a response.

Suggested first development battery: 12 multipart questions (two or three allowed filter/count/list operations), 8 ambiguity cases paired with 8 disambiguated controls, 8 supplier-alternative cases, and 8 replaceability/vulnerability cases. These counts are design targets, not claims of statistical power or authored items. Avoid held-out grouping/ranking/composition patterns in development. Fix item selection and rubric before model inference.

## Scoring

Executable parts: retain exact scoped SQL gold, verify all parts independently, and report all-parts accuracy plus per-part accuracy. Explicitly define row versus distinct-company counts. Never combine disjoint row observations into an invented facility.

Non-executable answers: each item gets a fact sheet of allowed claims with source row IDs, required unknowns, prohibited inferences, acceptable clarification questions and alternative defensible conclusions. Score each dimension 0 (wrong/absent), 1 (partly adequate), or 2 (complete):

- Evidence fidelity: all factual claims supported by supplied/source-eligible observations; no invented suppliers or attributes.
- Constraint handling: product/process/service/location requirements applied correctly; recorded certifications described accurately without claiming current qualification.
- Uncertainty: distinguishes missing data, conflicting records and real-world absence; does not substitute employment for capacity or supplier counts for import dependence.
- Reasoning completeness: explains the supported candidate/risk conclusion and what additional evidence would change it; answers every requested part.
- Clarification quality: asks the minimum question needed to resolve a material ambiguity, or answers directly when the paired control resolves it.

Mark not-applicable dimensions before scoring, never after seeing outputs. Report dimension scores and unsupported-claim incidence separately. Do not create a single success threshold until reviewers agree on anchored examples. Any fabricated decisive qualification/capacity/import claim is a critical error, reported regardless of other dimension scores.

Plausible alternatives are candidates for validation, not certified substitutes. Replaceability rankings require a stated proxy and evidence of compatibility/availability; lack of those data can prevent a ranking. Import dependence and capacity cannot be inferred from this workbook unless the required evidence is actually present.

## Adjudication and baseline requirements

Two reviewers independently score a pilot with model identities hidden; retain disagreements and adjudicated decisions. If only one reviewer is available, label the process single-reviewer rather than independent adjudication. An LLM judge may assist but cannot serve as the sole ground truth. Report agreement and examples of rubric changes; re-score all affected outputs consistently under a new version.

Before fine-tuned comparison, run the unchanged base on exactly the same questions, context, prompts and scoring version. Keep context-assisted scores separate from model-only scores. Include answerable controls to detect excessive abstention. Do not claim semantic competence from regex checks, SQL exactness alone or a passing 30-item sanity screen.

## Reviewable examples (illustrative, not dataset gold)

- Multipart: list suppliers with process P and certification C; count distinct names; identify missing certification evidence. Instantiate only permitted field combinations from the frozen registry, with exact scoped golds.
- Ambiguous: "Which supplier is best?" requires the product/specification and selection criteria. Control: supply explicit product and process requirements and ask for supported candidates, not an unsupported universal best.
- Alternatives: compare supplied candidate records against stated requirements. The gold fact sheet must identify which observations support plausibility and which customer-qualification/capacity evidence is missing.
- Vulnerability: ask whether records establish import exposure and capacity shortage. A correct response may provide a recorded-supplier-count proxy while explicitly declining the unsupported import/capacity conclusion.

# Development question review packet

Status: draft. No model responses or completed reviewer decisions are included.

Review source fidelity, question intent, acceptable answers and scoring anchors. Use accept, revise or reject in the separate CSV, with reviewer identity/date and reasons. An item decision is not a training or protected-evaluation release. Leave decisions blank until a human actually reviews the item.

All source observations are supplied in context. These diagnostics do not test closed-book recall.

## Scoring anchors

### Source: docs/DEV_AMBIGUITY_R1_DRAFT.md

# Referent ambiguity development diagnostic — draft r1

Sixteen items form eight ambiguity/control pairs. This is a provided-evidence
track: both pair members receive identical source-attributed company/location
records. The ambiguous question says "the supplier"; its control names one
company. The first sixteen dev-only records sorted by row ID were paired,
with the named control target alternating between the first and second record.
These are workbook observations, not externally verified company facts.

Dataset: `datasets_v3/dev_ambiguity_r1_draft_v3.jsonl`.
Builder: `finetune/build_dev_ambiguity_v3.py`.
Source pins: `validation_v3/DEV_AMBIGUITY_R1_DRAFT_MANIFEST.json`.
Independent source/pair checks: `validation_v3/DEV_AMBIGUITY_R1_DRAFT_CHECKS.json`.

## Proposed scoring anchors — fix before inference

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Evidence fidelity | Wrong company/location association or invented decisive location | Supported but incomplete location when giving a location | Any stated locations faithfully reflect the supplied records; a pure clarification invents nothing |
| Referent handling, ambiguous | Silently selects one company | Vague clarification without identifying the two available candidates | Asks which named candidate is intended, or labels both answers and explicitly notes the unresolved referent |
| Referent handling, control | Answers the wrong company or unnecessarily refuses to identify it | Correct company but adds an unnecessary clarification request | Directly identifies the named company |
| Response completeness, ambiguous | Neither useful clarification nor supported alternatives | Mentions ambiguity but gives no actionable clarification or complete alternatives | Minimal actionable company clarification, or both labeled recorded locations plus the limitation |
| Response completeness, control | No requested location | Partial supported location | Full recorded location for the named company |

Report dimension distributions separately for ambiguous items and controls.
Report wrong referent selection, unsupported claims, and unnecessary clarification
on controls separately. Do not aggregate these into a claimed success threshold
until human reviewers agree on the anchors. A pure clarification can receive full
credit on the ambiguous item; it cannot receive full credit on its control.

## Review and baseline prerequisites

Status is draft, not adjudicated gold. Human review must confirm question intent,
source alignment, acceptable alternative wording, and anchors before inference.
Freeze a versioned prompt containing only question and identical bounded context,
never the fact sheet or expected answer. Then collect an unchanged-base baseline
with no external execution. Blind model identity for rubric scoring; retain
independent reviewer disagreements or label a single-reviewer process accurately.
No inference, human scoring or training/checkpoint-selection change has occurred.

This narrow test does not establish alias disambiguation, conflicting-record
resolution, supplier analysis or memory-based recall. Dev entities are supplied
in context; this is not evidence that a closed-book model learned unseen facts.
The pairs are the natural analysis units, not sixteen independent trials. No
held-out grouping/ranking or certification/process combination is introduced.


### Source: docs/DEV_SUPPLIER_EVIDENCE_R1_DRAFT.md

# Supplier evidence development draft r1

Eight supplier-alternative questions and eight vulnerability questions now have
source-linked fact sheets. Each bounded context supplies three distinct dev
companies: two with one shared recorded process and one without that process in
its supplied record. Context includes only company/row identity, processes and
recorded employment. No certification/process combination is introduced.

Dataset: `datasets_v3/dev_supplier_evidence_r1_draft_v3.jsonl`.
Builder: `finetune/build_dev_supplier_evidence_v3.py`.
Pins and selection: `validation_v3/DEV_SUPPLIER_EVIDENCE_R1_DRAFT_MANIFEST.json`.
Source and membership checks: `validation_v3/DEV_SUPPLIER_EVIDENCE_R1_DRAFT_CHECKS.json`.

The alternative questions require supported process-based candidates and limits
on replaceability. The vulnerability questions cover production volume, current
qualification, engineering compatibility, near-term availability, imported inputs,
sole sourcing, replacement lead time and employment as a capacity proxy.
Every case requires supported partial answers as well as missing-evidence limits.
A blanket refusal therefore does not demonstrate success.

## Proposed anchored scoring, before inference

Score evidence fidelity, constraint handling, uncertainty and reasoning
completeness separately from 0 to 2. Clarification quality is not applicable.

- Evidence fidelity: 0 for a decisive invented or misattributed fact; 1 for minor
  unsupported details or incomplete attribution; 2 for claims grounded in the
  supplied records with clear record-based language.
- Constraint handling, alternatives: 0 for selecting the nonmatching company as
  an evidenced match or rejecting both matches; 1 for identifying only one match
  or incomplete treatment of the nonmatch; 2 for both matches and an accurate
  explanation that the nonmatch lacks this recorded evidence, not necessarily
  the real-world capability. These questions explicitly ask about every company.
- Constraint handling, vulnerability: 0 for selecting an unsupported match or
  rejecting both matches; 1 for identifying only one matching company; 2 for
  identifying both with their recorded process evidence. Discussion of the
  nonmatching company is optional because these questions concern the matches.
- Uncertainty: 0 for claiming the requested qualification/capacity/compatibility/
  import/sole-source conclusion is established; 1 for generic caution without
  identifying material missing evidence; 2 for the case-specific evidence limits
  and information needed to resolve them.
- Reasoning completeness: 0 for neither candidates nor relevant limitation; 1
  for only the supported answer or only the limitation; 2 for both with a clear
  connection between recorded process overlap and the limited conclusion.

Retain critical unsupported conclusions as separate flags even when other
scores are high. No overall success threshold is approved. Reviewers may accept
other defensible wording/conclusions supported by the bounded context; record
such cases rather than mechanically requiring the model to copy gold phrases.

## Required next work and limitations

Human review of these draft items and anchors precedes baseline inference. Freeze
question/context/prompt/rubric versions, hide model identities for review, retain
disagreements and identify single-reviewer scoring honestly if independent
reviewers are unavailable. Never include fact sheets in model prompts.

No inference or human scoring has been performed. These are provided-evidence
process-screening diagnostics, not qualified supplier recommendations, a complete
supply-chain risk analysis, or memory generalization measurements. Rows and
contexts recur across items, so sixteen items are not sixteen independent cases.
All risk questions deliberately probe insufficient evidence; a future extension
needs answerable risk controls with genuine supporting data, which cannot be
invented from this workbook. The process-screening subquestions are answerable
controls for partial evidence use, not positive controls for capacity or import
risk. Current observations do not establish real-world accuracy of the workbook.


## 1. DEV_AMBIG_R1_01_ambiguous

Kind: ambiguous; context SHA-256: `175b01b571f120af8ec0782e52ff17210a4a4b2669e0a85fc36069fca45e1d78`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "Flambeau Inc.", "recorded_location": "Madison, Morgan County", "row_id": 4}, {"company": "ACM Georgia LLC", "recorded_location": "Warrenton, Warren County", "row_id": 7}]

### Question

Where is the supplier located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_location": "Madison, Morgan County"
    },
    {
      "row_id": 7,
      "company": "ACM Georgia LLC",
      "recorded_location": "Warrenton, Warren County"
    }
  ],
  "required_behavior": "Ask which of the two named companies is intended; alternatively provide both labeled locations and state that the question does not identify one company.",
  "required_answer": null,
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": "Which company do you mean: Flambeau Inc. or ACM Georgia LLC?"
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 2. DEV_AMBIG_R1_01_control

Kind: control; context SHA-256: `175b01b571f120af8ec0782e52ff17210a4a4b2669e0a85fc36069fca45e1d78`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "Flambeau Inc.", "recorded_location": "Madison, Morgan County", "row_id": 4}, {"company": "ACM Georgia LLC", "recorded_location": "Warrenton, Warren County", "row_id": 7}]

### Question

Where is Flambeau Inc. located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_location": "Madison, Morgan County"
    },
    {
      "row_id": 7,
      "company": "ACM Georgia LLC",
      "recorded_location": "Warrenton, Warren County"
    }
  ],
  "required_behavior": "Answer the named company location directly from its record.",
  "required_answer": {
    "row_id": 4,
    "company": "Flambeau Inc.",
    "recorded_location": "Madison, Morgan County"
  },
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": null
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 3. DEV_AMBIG_R1_02_ambiguous

Kind: ambiguous; context SHA-256: `9813660cbca378dd70225d6dc32bbb4ffc830a731e3d7e92b49630c82f9478e0`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "AVS", "recorded_location": "Alpharetta, Forsyth County", "row_id": 16}, {"company": "Dorsett Industries Inc.", "recorded_location": "Dalton, Whitfield County", "row_id": 19}]

### Question

Where is the supplier located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 16,
      "company": "AVS",
      "recorded_location": "Alpharetta, Forsyth County"
    },
    {
      "row_id": 19,
      "company": "Dorsett Industries Inc.",
      "recorded_location": "Dalton, Whitfield County"
    }
  ],
  "required_behavior": "Ask which of the two named companies is intended; alternatively provide both labeled locations and state that the question does not identify one company.",
  "required_answer": null,
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": "Which company do you mean: AVS or Dorsett Industries Inc.?"
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 4. DEV_AMBIG_R1_02_control

Kind: control; context SHA-256: `9813660cbca378dd70225d6dc32bbb4ffc830a731e3d7e92b49630c82f9478e0`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "AVS", "recorded_location": "Alpharetta, Forsyth County", "row_id": 16}, {"company": "Dorsett Industries Inc.", "recorded_location": "Dalton, Whitfield County", "row_id": 19}]

### Question

Where is Dorsett Industries Inc. located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 16,
      "company": "AVS",
      "recorded_location": "Alpharetta, Forsyth County"
    },
    {
      "row_id": 19,
      "company": "Dorsett Industries Inc.",
      "recorded_location": "Dalton, Whitfield County"
    }
  ],
  "required_behavior": "Answer the named company location directly from its record.",
  "required_answer": {
    "row_id": 19,
    "company": "Dorsett Industries Inc.",
    "recorded_location": "Dalton, Whitfield County"
  },
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": null
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 5. DEV_AMBIG_R1_03_ambiguous

Kind: ambiguous; context SHA-256: `72fa55bb719459d566dc84116764bb5bf3a3d0c128b69b20a09c40aa67972172`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "Hollingsworth & Vose Co.", "recorded_location": "Hawkinsville, Bleckley County", "row_id": 77}, {"company": "Hwashin", "recorded_location": "LaGrange, Carroll County", "row_id": 79}]

### Question

Where is the supplier located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 77,
      "company": "Hollingsworth & Vose Co.",
      "recorded_location": "Hawkinsville, Bleckley County"
    },
    {
      "row_id": 79,
      "company": "Hwashin",
      "recorded_location": "LaGrange, Carroll County"
    }
  ],
  "required_behavior": "Ask which of the two named companies is intended; alternatively provide both labeled locations and state that the question does not identify one company.",
  "required_answer": null,
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": "Which company do you mean: Hollingsworth & Vose Co. or Hwashin?"
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 6. DEV_AMBIG_R1_03_control

Kind: control; context SHA-256: `72fa55bb719459d566dc84116764bb5bf3a3d0c128b69b20a09c40aa67972172`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "Hollingsworth & Vose Co.", "recorded_location": "Hawkinsville, Bleckley County", "row_id": 77}, {"company": "Hwashin", "recorded_location": "LaGrange, Carroll County", "row_id": 79}]

### Question

Where is Hollingsworth & Vose Co. located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 77,
      "company": "Hollingsworth & Vose Co.",
      "recorded_location": "Hawkinsville, Bleckley County"
    },
    {
      "row_id": 79,
      "company": "Hwashin",
      "recorded_location": "LaGrange, Carroll County"
    }
  ],
  "required_behavior": "Answer the named company location directly from its record.",
  "required_answer": {
    "row_id": 77,
    "company": "Hollingsworth & Vose Co.",
    "recorded_location": "Hawkinsville, Bleckley County"
  },
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": null
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 7. DEV_AMBIG_R1_04_ambiguous

Kind: ambiguous; context SHA-256: `1462d3ea521f65a6a7bcaf20df0307ad6314cecffdf5249bcd8259eaf34c17a7`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "Daesol Material Georgia, LLC", "recorded_location": "Duluth, Gwinnett County", "row_id": 81}, {"company": "Linde + Wiemann", "recorded_location": "Dublin, Laurens County", "row_id": 102}]

### Question

Where is the supplier located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 81,
      "company": "Daesol Material Georgia, LLC",
      "recorded_location": "Duluth, Gwinnett County"
    },
    {
      "row_id": 102,
      "company": "Linde + Wiemann",
      "recorded_location": "Dublin, Laurens County"
    }
  ],
  "required_behavior": "Ask which of the two named companies is intended; alternatively provide both labeled locations and state that the question does not identify one company.",
  "required_answer": null,
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": "Which company do you mean: Daesol Material Georgia, LLC or Linde + Wiemann?"
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 8. DEV_AMBIG_R1_04_control

Kind: control; context SHA-256: `1462d3ea521f65a6a7bcaf20df0307ad6314cecffdf5249bcd8259eaf34c17a7`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "Daesol Material Georgia, LLC", "recorded_location": "Duluth, Gwinnett County", "row_id": 81}, {"company": "Linde + Wiemann", "recorded_location": "Dublin, Laurens County", "row_id": 102}]

### Question

Where is Linde + Wiemann located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 81,
      "company": "Daesol Material Georgia, LLC",
      "recorded_location": "Duluth, Gwinnett County"
    },
    {
      "row_id": 102,
      "company": "Linde + Wiemann",
      "recorded_location": "Dublin, Laurens County"
    }
  ],
  "required_behavior": "Answer the named company location directly from its record.",
  "required_answer": {
    "row_id": 102,
    "company": "Linde + Wiemann",
    "recorded_location": "Dublin, Laurens County"
  },
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": null
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 9. DEV_AMBIG_R1_05_ambiguous

Kind: ambiguous; context SHA-256: `f0ae595a802178a59c5e85319eeebd4226ea366ff834d3a9484692b78bd0f8a4`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "Magna International", "recorded_location": "Carrollton, Carroll County", "row_id": 108}, {"company": "Peterson Spring", "recorded_location": "Athens, Clarke County", "row_id": 113}]

### Question

Where is the supplier located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 108,
      "company": "Magna International",
      "recorded_location": "Carrollton, Carroll County"
    },
    {
      "row_id": 113,
      "company": "Peterson Spring",
      "recorded_location": "Athens, Clarke County"
    }
  ],
  "required_behavior": "Ask which of the two named companies is intended; alternatively provide both labeled locations and state that the question does not identify one company.",
  "required_answer": null,
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": "Which company do you mean: Magna International or Peterson Spring?"
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 10. DEV_AMBIG_R1_05_control

Kind: control; context SHA-256: `f0ae595a802178a59c5e85319eeebd4226ea366ff834d3a9484692b78bd0f8a4`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "Magna International", "recorded_location": "Carrollton, Carroll County", "row_id": 108}, {"company": "Peterson Spring", "recorded_location": "Athens, Clarke County", "row_id": 113}]

### Question

Where is Magna International located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 108,
      "company": "Magna International",
      "recorded_location": "Carrollton, Carroll County"
    },
    {
      "row_id": 113,
      "company": "Peterson Spring",
      "recorded_location": "Athens, Clarke County"
    }
  ],
  "required_behavior": "Answer the named company location directly from its record.",
  "required_answer": {
    "row_id": 108,
    "company": "Magna International",
    "recorded_location": "Carrollton, Carroll County"
  },
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": null
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 11. DEV_AMBIG_R1_06_ambiguous

Kind: ambiguous; context SHA-256: `a80b73ae09336d0e1db84600cdad73dd12d179451e8c9e2a2e1415e9a4f0e0f7`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "Pirelli Tire North America LLC", "recorded_location": "Albany, Dougherty County", "row_id": 117}, {"company": "Nile Automotive", "recorded_location": "Cumming, Forsyth County", "row_id": 124}]

### Question

Where is the supplier located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 117,
      "company": "Pirelli Tire North America LLC",
      "recorded_location": "Albany, Dougherty County"
    },
    {
      "row_id": 124,
      "company": "Nile Automotive",
      "recorded_location": "Cumming, Forsyth County"
    }
  ],
  "required_behavior": "Ask which of the two named companies is intended; alternatively provide both labeled locations and state that the question does not identify one company.",
  "required_answer": null,
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": "Which company do you mean: Pirelli Tire North America LLC or Nile Automotive?"
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 12. DEV_AMBIG_R1_06_control

Kind: control; context SHA-256: `a80b73ae09336d0e1db84600cdad73dd12d179451e8c9e2a2e1415e9a4f0e0f7`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "Pirelli Tire North America LLC", "recorded_location": "Albany, Dougherty County", "row_id": 117}, {"company": "Nile Automotive", "recorded_location": "Cumming, Forsyth County", "row_id": 124}]

### Question

Where is Nile Automotive located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 117,
      "company": "Pirelli Tire North America LLC",
      "recorded_location": "Albany, Dougherty County"
    },
    {
      "row_id": 124,
      "company": "Nile Automotive",
      "recorded_location": "Cumming, Forsyth County"
    }
  ],
  "required_behavior": "Answer the named company location directly from its record.",
  "required_answer": {
    "row_id": 124,
    "company": "Nile Automotive",
    "recorded_location": "Cumming, Forsyth County"
  },
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": null
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 13. DEV_AMBIG_R1_07_ambiguous

Kind: ambiguous; context SHA-256: `a170ebf3a8f2abed75382d9a1759aab56df884d5888631d6a1bab98889e9d2e9`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "OTR Wheel Engineering Inc.", "recorded_location": "Rome, Floyd County", "row_id": 132}, {"company": "SungEel Recycling Park Georgia", "recorded_location": "Duluth, Gwinnett County", "row_id": 170}]

### Question

Where is the supplier located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 132,
      "company": "OTR Wheel Engineering Inc.",
      "recorded_location": "Rome, Floyd County"
    },
    {
      "row_id": 170,
      "company": "SungEel Recycling Park Georgia",
      "recorded_location": "Duluth, Gwinnett County"
    }
  ],
  "required_behavior": "Ask which of the two named companies is intended; alternatively provide both labeled locations and state that the question does not identify one company.",
  "required_answer": null,
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": "Which company do you mean: OTR Wheel Engineering Inc. or SungEel Recycling Park Georgia?"
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 14. DEV_AMBIG_R1_07_control

Kind: control; context SHA-256: `a170ebf3a8f2abed75382d9a1759aab56df884d5888631d6a1bab98889e9d2e9`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "OTR Wheel Engineering Inc.", "recorded_location": "Rome, Floyd County", "row_id": 132}, {"company": "SungEel Recycling Park Georgia", "recorded_location": "Duluth, Gwinnett County", "row_id": 170}]

### Question

Where is OTR Wheel Engineering Inc. located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 132,
      "company": "OTR Wheel Engineering Inc.",
      "recorded_location": "Rome, Floyd County"
    },
    {
      "row_id": 170,
      "company": "SungEel Recycling Park Georgia",
      "recorded_location": "Duluth, Gwinnett County"
    }
  ],
  "required_behavior": "Answer the named company location directly from its record.",
  "required_answer": {
    "row_id": 132,
    "company": "OTR Wheel Engineering Inc.",
    "recorded_location": "Rome, Floyd County"
  },
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": null
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 15. DEV_AMBIG_R1_08_ambiguous

Kind: ambiguous; context SHA-256: `c62375febf8eeda76417aaf8c2732efc395a5b9b0dcdc489d187e935ec5bd7ec`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "TCI Powder Coatings", "recorded_location": "Ellaville, Schley County", "row_id": 173}, {"company": "Wabash National Corp.", "recorded_location": "Ellenwood, Clayton County", "row_id": 194}]

### Question

Where is the supplier located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 173,
      "company": "TCI Powder Coatings",
      "recorded_location": "Ellaville, Schley County"
    },
    {
      "row_id": 194,
      "company": "Wabash National Corp.",
      "recorded_location": "Ellenwood, Clayton County"
    }
  ],
  "required_behavior": "Ask which of the two named companies is intended; alternatively provide both labeled locations and state that the question does not identify one company.",
  "required_answer": null,
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": "Which company do you mean: TCI Powder Coatings or Wabash National Corp.?"
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 16. DEV_AMBIG_R1_08_control

Kind: control; context SHA-256: `c62375febf8eeda76417aaf8c2732efc395a5b9b0dcdc489d187e935ec5bd7ec`

### Model-visible evidence

Workbook observations, not independently verified current facts. Each row is a source record, not proof of a distinct facility.
[{"company": "TCI Powder Coatings", "recorded_location": "Ellaville, Schley County", "row_id": 173}, {"company": "Wabash National Corp.", "recorded_location": "Ellenwood, Clayton County", "row_id": 194}]

### Question

Where is Wabash National Corp. located, according to these records?

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 173,
      "company": "TCI Powder Coatings",
      "recorded_location": "Ellaville, Schley County"
    },
    {
      "row_id": 194,
      "company": "Wabash National Corp.",
      "recorded_location": "Ellenwood, Clayton County"
    }
  ],
  "required_behavior": "Answer the named company location directly from its record.",
  "required_answer": {
    "row_id": 194,
    "company": "Wabash National Corp.",
    "recorded_location": "Ellenwood, Clayton County"
  },
  "prohibited_inferences": [
    "Silently choose one company for an unresolved referent.",
    "Treat recorded location as independently verified current location.",
    "Add unsupported geography or claim records establish distinct facilities."
  ],
  "acceptable_clarification": null
}

```

### Proposed scoring metadata

```json

{
  "method": "human_anchored_dimensions_0_1_2",
  "dimensions": [
    "evidence_fidelity",
    "referent_handling",
    "response_completeness"
  ],
  "not_applicable": [
    "supplier_qualification",
    "capacity",
    "import_dependence"
  ],
  "aggregate": "Report each dimension by kind and paired success; no pooled threshold.",
  "regex_is_not_semantic_ground_truth": true
}

```

## 17. DEV_SUPPLIER_R1_01_alternatives

Kind: alternatives; context SHA-256: `875481cd724640a289c3f19194f8323a47105421d040964b4666925b55142575`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "Linde + Wiemann", "recorded_employment": 515, "recorded_processes": "CNC Machining; Grinding; Turning", "row_id": 102}, {"company": "Peterson Spring", "recorded_employment": 150, "recorded_processes": "CNC Machining; Grinding; Turning", "row_id": 113}]

### Question

Within the supplied records only, identify candidates worth investigating for CNC Machining. Explain what supports including or not including each named company, and whether these records alone establish that the candidates can replace one another.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 102,
      "company": "Linde + Wiemann",
      "recorded_processes": "CNC Machining; Grinding; Turning",
      "recorded_employment": 515
    },
    {
      "row_id": 113,
      "company": "Peterson Spring",
      "recorded_processes": "CNC Machining; Grinding; Turning",
      "recorded_employment": 150
    }
  ],
  "supported_candidate_row_ids": [
    102,
    113
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Product specifications and compatibility",
    "Current customer qualification",
    "Available capacity, required volume and delivery timing"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 18. DEV_SUPPLIER_R1_01_vulnerability

Kind: vulnerability; context SHA-256: `875481cd724640a289c3f19194f8323a47105421d040964b4666925b55142575`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "Linde + Wiemann", "recorded_employment": 515, "recorded_processes": "CNC Machining; Grinding; Turning", "row_id": 102}, {"company": "Peterson Spring", "recorded_employment": 150, "recorded_processes": "CNC Machining; Grinding; Turning", "row_id": 113}]

### Question

Consider the supplied companies with recorded process CNC Machining. Does the recorded employment establish that either matching candidate can absorb the other candidate's production volume? State what the records do support and the additional evidence needed.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 102,
      "company": "Linde + Wiemann",
      "recorded_processes": "CNC Machining; Grinding; Turning",
      "recorded_employment": 515
    },
    {
      "row_id": 113,
      "company": "Peterson Spring",
      "recorded_processes": "CNC Machining; Grinding; Turning",
      "recorded_employment": 150
    }
  ],
  "supported_candidate_row_ids": [
    102,
    113
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Required volume, utilization, equipment throughput and available capacity"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 19. DEV_SUPPLIER_R1_02_alternatives

Kind: alternatives; context SHA-256: `fbeb6f00214bf0e48b921e2afade63c621bbc8c8d1c07df88d24c039da05d9f4`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "AVS", "recorded_employment": 310, "recorded_processes": "Compression Molding; Polymer Production", "row_id": 16}, {"company": "Daesol Material Georgia, LLC", "recorded_employment": 90, "recorded_processes": "Compression Molding; Polymer Production", "row_id": 81}]

### Question

Within the supplied records only, identify candidates worth investigating for Compression Molding. Explain what supports including or not including each named company, and whether these records alone establish that the candidates can replace one another.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 16,
      "company": "AVS",
      "recorded_processes": "Compression Molding; Polymer Production",
      "recorded_employment": 310
    },
    {
      "row_id": 81,
      "company": "Daesol Material Georgia, LLC",
      "recorded_processes": "Compression Molding; Polymer Production",
      "recorded_employment": 90
    }
  ],
  "supported_candidate_row_ids": [
    16,
    81
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Product specifications and compatibility",
    "Current customer qualification",
    "Available capacity, required volume and delivery timing"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 20. DEV_SUPPLIER_R1_02_vulnerability

Kind: vulnerability; context SHA-256: `fbeb6f00214bf0e48b921e2afade63c621bbc8c8d1c07df88d24c039da05d9f4`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "AVS", "recorded_employment": 310, "recorded_processes": "Compression Molding; Polymer Production", "row_id": 16}, {"company": "Daesol Material Georgia, LLC", "recorded_employment": 90, "recorded_processes": "Compression Molding; Polymer Production", "row_id": 81}]

### Question

Consider the supplied companies with recorded process Compression Molding. Does this evidence establish that the matching candidates are currently customer-qualified substitutes? State what the records do support and the additional evidence needed.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 16,
      "company": "AVS",
      "recorded_processes": "Compression Molding; Polymer Production",
      "recorded_employment": 310
    },
    {
      "row_id": 81,
      "company": "Daesol Material Georgia, LLC",
      "recorded_processes": "Compression Molding; Polymer Production",
      "recorded_employment": 90
    }
  ],
  "supported_candidate_row_ids": [
    16,
    81
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Current customer-specific qualification and applicable approvals"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 21. DEV_SUPPLIER_R1_03_alternatives

Kind: alternatives; context SHA-256: `875481cd724640a289c3f19194f8323a47105421d040964b4666925b55142575`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "Linde + Wiemann", "recorded_employment": 515, "recorded_processes": "CNC Machining; Grinding; Turning", "row_id": 102}, {"company": "Peterson Spring", "recorded_employment": 150, "recorded_processes": "CNC Machining; Grinding; Turning", "row_id": 113}]

### Question

Within the supplied records only, identify candidates worth investigating for Grinding. Explain what supports including or not including each named company, and whether these records alone establish that the candidates can replace one another.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 102,
      "company": "Linde + Wiemann",
      "recorded_processes": "CNC Machining; Grinding; Turning",
      "recorded_employment": 515
    },
    {
      "row_id": 113,
      "company": "Peterson Spring",
      "recorded_processes": "CNC Machining; Grinding; Turning",
      "recorded_employment": 150
    }
  ],
  "supported_candidate_row_ids": [
    102,
    113
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Product specifications and compatibility",
    "Current customer qualification",
    "Available capacity, required volume and delivery timing"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 22. DEV_SUPPLIER_R1_03_vulnerability

Kind: vulnerability; context SHA-256: `875481cd724640a289c3f19194f8323a47105421d040964b4666925b55142575`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "Linde + Wiemann", "recorded_employment": 515, "recorded_processes": "CNC Machining; Grinding; Turning", "row_id": 102}, {"company": "Peterson Spring", "recorded_employment": 150, "recorded_processes": "CNC Machining; Grinding; Turning", "row_id": 113}]

### Question

Consider the supplied companies with recorded process Grinding. Does this evidence establish that their products are interchangeable without engineering changes? State what the records do support and the additional evidence needed.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 102,
      "company": "Linde + Wiemann",
      "recorded_processes": "CNC Machining; Grinding; Turning",
      "recorded_employment": 515
    },
    {
      "row_id": 113,
      "company": "Peterson Spring",
      "recorded_processes": "CNC Machining; Grinding; Turning",
      "recorded_employment": 150
    }
  ],
  "supported_candidate_row_ids": [
    102,
    113
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Part specifications, materials, tolerances and validation evidence"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 23. DEV_SUPPLIER_R1_04_alternatives

Kind: alternatives; context SHA-256: `bbb5564b9d5b4115c93c596dc3a57712a1a0b723102cdad46136f23605d25d88`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "Nile Automotive", "recorded_employment": 300, "recorded_processes": "Injection Molding; Interior Assembly", "row_id": 124}, {"company": "SungEel Recycling Park Georgia", "recorded_employment": 650, "recorded_processes": "Battery Recycling Logistics; Injection Molding; Interior Assembly; Material Blending; Refining", "row_id": 170}]

### Question

Within the supplied records only, identify candidates worth investigating for Injection Molding. Explain what supports including or not including each named company, and whether these records alone establish that the candidates can replace one another.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 124,
      "company": "Nile Automotive",
      "recorded_processes": "Injection Molding; Interior Assembly",
      "recorded_employment": 300
    },
    {
      "row_id": 170,
      "company": "SungEel Recycling Park Georgia",
      "recorded_processes": "Battery Recycling Logistics; Injection Molding; Interior Assembly; Material Blending; Refining",
      "recorded_employment": 650
    }
  ],
  "supported_candidate_row_ids": [
    124,
    170
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Product specifications and compatibility",
    "Current customer qualification",
    "Available capacity, required volume and delivery timing"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 24. DEV_SUPPLIER_R1_04_vulnerability

Kind: vulnerability; context SHA-256: `bbb5564b9d5b4115c93c596dc3a57712a1a0b723102cdad46136f23605d25d88`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "Nile Automotive", "recorded_employment": 300, "recorded_processes": "Injection Molding; Interior Assembly", "row_id": 124}, {"company": "SungEel Recycling Park Georgia", "recorded_employment": 650, "recorded_processes": "Battery Recycling Logistics; Injection Molding; Interior Assembly; Material Blending; Refining", "row_id": 170}]

### Question

Consider the supplied companies with recorded process Injection Molding. Does this evidence establish that either matching candidate has spare capacity available this month? State what the records do support and the additional evidence needed.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 124,
      "company": "Nile Automotive",
      "recorded_processes": "Injection Molding; Interior Assembly",
      "recorded_employment": 300
    },
    {
      "row_id": 170,
      "company": "SungEel Recycling Park Georgia",
      "recorded_processes": "Battery Recycling Logistics; Injection Molding; Interior Assembly; Material Blending; Refining",
      "recorded_employment": 650
    }
  ],
  "supported_candidate_row_ids": [
    124,
    170
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Current utilization, available equipment and delivery commitments"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 25. DEV_SUPPLIER_R1_05_alternatives

Kind: alternatives; context SHA-256: `bbb5564b9d5b4115c93c596dc3a57712a1a0b723102cdad46136f23605d25d88`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "Nile Automotive", "recorded_employment": 300, "recorded_processes": "Injection Molding; Interior Assembly", "row_id": 124}, {"company": "SungEel Recycling Park Georgia", "recorded_employment": 650, "recorded_processes": "Battery Recycling Logistics; Injection Molding; Interior Assembly; Material Blending; Refining", "row_id": 170}]

### Question

Within the supplied records only, identify candidates worth investigating for Interior Assembly. Explain what supports including or not including each named company, and whether these records alone establish that the candidates can replace one another.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 124,
      "company": "Nile Automotive",
      "recorded_processes": "Injection Molding; Interior Assembly",
      "recorded_employment": 300
    },
    {
      "row_id": 170,
      "company": "SungEel Recycling Park Georgia",
      "recorded_processes": "Battery Recycling Logistics; Injection Molding; Interior Assembly; Material Blending; Refining",
      "recorded_employment": 650
    }
  ],
  "supported_candidate_row_ids": [
    124,
    170
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Product specifications and compatibility",
    "Current customer qualification",
    "Available capacity, required volume and delivery timing"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 26. DEV_SUPPLIER_R1_05_vulnerability

Kind: vulnerability; context SHA-256: `bbb5564b9d5b4115c93c596dc3a57712a1a0b723102cdad46136f23605d25d88`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "Nile Automotive", "recorded_employment": 300, "recorded_processes": "Injection Molding; Interior Assembly", "row_id": 124}, {"company": "SungEel Recycling Park Georgia", "recorded_employment": 650, "recorded_processes": "Battery Recycling Logistics; Injection Molding; Interior Assembly; Material Blending; Refining", "row_id": 170}]

### Question

Consider the supplied companies with recorded process Interior Assembly. Does this evidence establish whether the matching candidates depend on imported inputs? State what the records do support and the additional evidence needed.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 124,
      "company": "Nile Automotive",
      "recorded_processes": "Injection Molding; Interior Assembly",
      "recorded_employment": 300
    },
    {
      "row_id": 170,
      "company": "SungEel Recycling Park Georgia",
      "recorded_processes": "Battery Recycling Logistics; Injection Molding; Interior Assembly; Material Blending; Refining",
      "recorded_employment": 650
    }
  ],
  "supported_candidate_row_ids": [
    124,
    170
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Input origins, procurement dependencies and import shares"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 27. DEV_SUPPLIER_R1_06_alternatives

Kind: alternatives; context SHA-256: `cc617a24bd1be17881874c28bed1451e7c3b003338149de8f2869008856bf031`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "Hollingsworth & Vose Co.", "recorded_employment": 400, "recorded_processes": "Electrode Coating; Material Blending", "row_id": 77}, {"company": "SungEel Recycling Park Georgia", "recorded_employment": 650, "recorded_processes": "Battery Recycling Logistics; Injection Molding; Interior Assembly; Material Blending; Refining", "row_id": 170}]

### Question

Within the supplied records only, identify candidates worth investigating for Material Blending. Explain what supports including or not including each named company, and whether these records alone establish that the candidates can replace one another.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 77,
      "company": "Hollingsworth & Vose Co.",
      "recorded_processes": "Electrode Coating; Material Blending",
      "recorded_employment": 400
    },
    {
      "row_id": 170,
      "company": "SungEel Recycling Park Georgia",
      "recorded_processes": "Battery Recycling Logistics; Injection Molding; Interior Assembly; Material Blending; Refining",
      "recorded_employment": 650
    }
  ],
  "supported_candidate_row_ids": [
    77,
    170
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Product specifications and compatibility",
    "Current customer qualification",
    "Available capacity, required volume and delivery timing"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 28. DEV_SUPPLIER_R1_06_vulnerability

Kind: vulnerability; context SHA-256: `cc617a24bd1be17881874c28bed1451e7c3b003338149de8f2869008856bf031`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "Hollingsworth & Vose Co.", "recorded_employment": 400, "recorded_processes": "Electrode Coating; Material Blending", "row_id": 77}, {"company": "SungEel Recycling Park Georgia", "recorded_employment": 650, "recorded_processes": "Battery Recycling Logistics; Injection Molding; Interior Assembly; Material Blending; Refining", "row_id": 170}]

### Question

Consider the supplied companies with recorded process Material Blending. Does this evidence establish that losing one matching candidate would leave the customer with no alternative supplier? State what the records do support and the additional evidence needed.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 77,
      "company": "Hollingsworth & Vose Co.",
      "recorded_processes": "Electrode Coating; Material Blending",
      "recorded_employment": 400
    },
    {
      "row_id": 170,
      "company": "SungEel Recycling Park Georgia",
      "recorded_processes": "Battery Recycling Logistics; Injection Molding; Interior Assembly; Material Blending; Refining",
      "recorded_employment": 650
    }
  ],
  "supported_candidate_row_ids": [
    77,
    170
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Customer sourcing relationships and complete qualified-alternative coverage"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 29. DEV_SUPPLIER_R1_07_alternatives

Kind: alternatives; context SHA-256: `fbeb6f00214bf0e48b921e2afade63c621bbc8c8d1c07df88d24c039da05d9f4`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "AVS", "recorded_employment": 310, "recorded_processes": "Compression Molding; Polymer Production", "row_id": 16}, {"company": "Daesol Material Georgia, LLC", "recorded_employment": 90, "recorded_processes": "Compression Molding; Polymer Production", "row_id": 81}]

### Question

Within the supplied records only, identify candidates worth investigating for Polymer Production. Explain what supports including or not including each named company, and whether these records alone establish that the candidates can replace one another.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 16,
      "company": "AVS",
      "recorded_processes": "Compression Molding; Polymer Production",
      "recorded_employment": 310
    },
    {
      "row_id": 81,
      "company": "Daesol Material Georgia, LLC",
      "recorded_processes": "Compression Molding; Polymer Production",
      "recorded_employment": 90
    }
  ],
  "supported_candidate_row_ids": [
    16,
    81
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Product specifications and compatibility",
    "Current customer qualification",
    "Available capacity, required volume and delivery timing"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 30. DEV_SUPPLIER_R1_07_vulnerability

Kind: vulnerability; context SHA-256: `fbeb6f00214bf0e48b921e2afade63c621bbc8c8d1c07df88d24c039da05d9f4`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "AVS", "recorded_employment": 310, "recorded_processes": "Compression Molding; Polymer Production", "row_id": 16}, {"company": "Daesol Material Georgia, LLC", "recorded_employment": 90, "recorded_processes": "Compression Molding; Polymer Production", "row_id": 81}]

### Question

Consider the supplied companies with recorded process Polymer Production. Does this evidence establish which matching candidate could replace the other sooner? State what the records do support and the additional evidence needed.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 16,
      "company": "AVS",
      "recorded_processes": "Compression Molding; Polymer Production",
      "recorded_employment": 310
    },
    {
      "row_id": 81,
      "company": "Daesol Material Georgia, LLC",
      "recorded_processes": "Compression Molding; Polymer Production",
      "recorded_employment": 90
    }
  ],
  "supported_candidate_row_ids": [
    16,
    81
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Current stock, qualification duration, production scheduling and logistics"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 31. DEV_SUPPLIER_R1_08_alternatives

Kind: alternatives; context SHA-256: `875481cd724640a289c3f19194f8323a47105421d040964b4666925b55142575`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "Linde + Wiemann", "recorded_employment": 515, "recorded_processes": "CNC Machining; Grinding; Turning", "row_id": 102}, {"company": "Peterson Spring", "recorded_employment": 150, "recorded_processes": "CNC Machining; Grinding; Turning", "row_id": 113}]

### Question

Within the supplied records only, identify candidates worth investigating for Turning. Explain what supports including or not including each named company, and whether these records alone establish that the candidates can replace one another.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 102,
      "company": "Linde + Wiemann",
      "recorded_processes": "CNC Machining; Grinding; Turning",
      "recorded_employment": 515
    },
    {
      "row_id": 113,
      "company": "Peterson Spring",
      "recorded_processes": "CNC Machining; Grinding; Turning",
      "recorded_employment": 150
    }
  ],
  "supported_candidate_row_ids": [
    102,
    113
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Product specifications and compatibility",
    "Current customer qualification",
    "Available capacity, required volume and delivery timing"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

## 32. DEV_SUPPLIER_R1_08_vulnerability

Kind: vulnerability; context SHA-256: `875481cd724640a289c3f19194f8323a47105421d040964b4666925b55142575`

### Model-visible evidence

These are bounded workbook observations, not independently verified current facts. Rows do not by themselves establish distinct facilities.
[{"company": "Flambeau Inc.", "recorded_employment": 700, "recorded_processes": "Assembly & Integration", "row_id": 4}, {"company": "Linde + Wiemann", "recorded_employment": 515, "recorded_processes": "CNC Machining; Grinding; Turning", "row_id": 102}, {"company": "Peterson Spring", "recorded_employment": 150, "recorded_processes": "CNC Machining; Grinding; Turning", "row_id": 113}]

### Question

Consider the supplied companies with recorded process Turning. Would choosing the matching candidate with the larger recorded employment establish greater available production capacity? State what the records do support and the additional evidence needed.

### Reviewer-only fact sheet — never include in the model prompt

```json

{
  "allowed_claims": [
    {
      "row_id": 4,
      "company": "Flambeau Inc.",
      "recorded_processes": "Assembly & Integration",
      "recorded_employment": 700
    },
    {
      "row_id": 102,
      "company": "Linde + Wiemann",
      "recorded_processes": "CNC Machining; Grinding; Turning",
      "recorded_employment": 515
    },
    {
      "row_id": 113,
      "company": "Peterson Spring",
      "recorded_processes": "CNC Machining; Grinding; Turning",
      "recorded_employment": 150
    }
  ],
  "supported_candidate_row_ids": [
    102,
    113
  ],
  "not_supported_by_recorded_process_row_ids": [
    4
  ],
  "required_unknowns": [
    "Comparable employment scope/date, process throughput and spare capacity"
  ],
  "required_supported_partial_answer": "Identify both matching companies and their recorded process evidence.",
  "prohibited_inferences": [
    "Process overlap proves a qualified or interchangeable substitute.",
    "Recorded employment measures available capacity.",
    "Missing process evidence proves the company cannot perform it.",
    "The bounded context is an exhaustive supplier census.",
    "Recorded processes establish procurement origins, sole sourcing or delivery timing."
  ]
}

```

### Proposed scoring metadata

```json

{
  "dimensions": [
    "evidence_fidelity",
    "constraint_handling",
    "uncertainty",
    "reasoning_completeness"
  ],
  "scale": [
    0,
    1,
    2
  ],
  "clarification_quality": "not_applicable",
  "critical_errors": [
    "Unsupported decisive qualification, compatibility, capacity, import or sole-source claim"
  ],
  "blanket_refusal": "Cannot receive full completeness credit without the supported partial answer.",
  "method": "human_review_required_no_regex_semantic_scoring"
}

```

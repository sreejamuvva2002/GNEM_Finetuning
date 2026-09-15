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

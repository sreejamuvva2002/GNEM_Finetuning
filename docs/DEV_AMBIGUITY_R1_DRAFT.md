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

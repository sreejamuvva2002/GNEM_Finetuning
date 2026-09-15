# Multipart development baseline — part-level audit

All 12 saved score records were reproduced exactly with the retained grader
hashes verified. Dataset and prediction hashes match the original baseline
summary. No inference was run and historical results were not rewritten.

| Measure | Result |
|---|---:|
| All-parts question accuracy | 0/12 |
| Strict question accuracy | 0/12 |
| Part accuracy | 3/30 (10%) |
| Count-part accuracy | 3/18 (16.7%) |
| Company-list part accuracy | 0/12 |
| Question format compliance | 12/12 |
| Part format compliance | 30/30 |
| Truncated questions | 0/12 |
| Empty company-list predictions | 4/12 |
| Nonempty company-list golds | 12/12 |

The base model sometimes answered count components correctly, but no question
had every part correct. Correct format did not imply factual correctness.
Eight list predictions were nonempty and incorrect; four were empty omissions.
Do not describe the entire multipart baseline as blanket abstention, and do not
infer that every incorrect nonempty list is entirely fabricated: it can also
omit required companies or combine correct and incorrect members.

The 12 questions recombine existing development components. Parts and questions
are correlated; the denominators are descriptive, not independent model runs.
This is a multipart diagnostic, not an independent test of unseen facts, a
checkpoint-selection change, or evidence of final fine-tuned performance.

Reproduction script: `finetune/audit_dev_multipart_r1.py`.
Pinned inputs and summary: `audit.json`; per-part gold/output details: `parts.jsonl`.
The script refuses to replace an existing audit directory.

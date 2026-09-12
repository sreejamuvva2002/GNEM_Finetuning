# Development decisions — V3 A-002

## 2026-09-11: micro inference output contract, before full baseline runs

Initial micro runs are retained under results_v3/micro/. The oracle-context model returned correct source values inside explanatory prose, which the conservative exact parser rejected. The question referenced a record number absent from the context. These are harness/prompt findings, not final model scores.

Revision: include the source row identifier in oracle context; request JSON scalar/list outputs consistently for all model-only and context conditions, while preserving SQL output requirements for SQL conditions. Freeze the revised templates before the new development runs. Training targets and protected test outcomes did not inform this change. Keep strict value/set parsing and report parse failures separately; no substring-containment correctness was introduced.

Q42 approval remains pending at the user's explicit direction. Final training is not released. All smoke runs are diagnostic two-step runs and cannot count toward the 18 final runs.

## Shared SQL catalogue correction

Static protocol comparison found the initial SQL runner omitted the shared runtime vocabulary required by README Phase 31. Retain earlier runs as pilots, not protocol-complete baselines. The corrected catalogue contains full-source categorical/process/service/certification vocabularies without company-to-value associations and is identical for SQL conditions. Freeze its hash with prompts before corrected runs. No model score motivated vocabulary selection; the allowed fields are explicit in the builder.

## Smoke-test sampling coverage correction

The first two-step smoke suite sampled the first eight examples. Because BC/BD concatenate sources, this did not exercise every component of each mixture. The first suite and adapter reload evidence are retained in archive/smoke_prefix_pilot_2026-09-11/. Repeat the smoke suite with eight deterministic positions spanning each complete recipe and four positions spanning development targets; record exact indices. This is an engineering test change, not final-model selection.

## Development-driven parser revision A002.2 — 12 September 2026

Bounded matched-quote removal and requested-key object unwrapping separate semantic accuracy from original JSON format compliance. Wrong values, extra/missing members, boolean substitutions and nonstandard JSON constants remain rejected as specified. Thirty parser tests pass. Rescoring retained dev outputs recovers 30 quote-wrapped answers and one named object: oracle semantic accuracy 245/255 (96.1%), previously 214/255. Ten boolean-surface differences remain incorrect. SQL verdicts unchanged; SQL format is N/A under the JSON answer contract. No model inference repeated or protected scoring performed. Versioned report: results_v3/dev/REPORT_A002_r2.md; full changes and code hashes accompany it.

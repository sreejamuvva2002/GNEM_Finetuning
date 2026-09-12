# CONTEXT_BUDGET_v3

Phase 6 — context renderer and token budget for **`base_ctx_oracle`**.

`base_ctx_oracle` is an **oracle-context baseline** — a **retrieval-grounded factual upper bound**. The correct row is supplied by construction, so it measures grounded answering, not retrieval quality. It is never a RAG baseline, a retrieval-system benchmark, or a retriever benchmark. It applies to **factual probes only**; global structured questions compare against `base_sql` / `base_sql_5shot`, which are not implemented in this phase.

## Frozen inputs

```text
datasets_v3/gnem_v3.sqlite   7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b
canonical_records_v3.jsonl   42851c0a2e93209ac5d37e73ce07447009e038b9db625004212722d7738e6488
company_split_groups_v3.csv  a59d673ac9acafd1f70f60cf560491c32d8d11bacdab3c9bc5d77016b536b701
finetune/kb_v3.py            2f13bc61212c7bd65103cb0c9f2a31c482e1589ec6f0fae47df9fe08ef9c7100
```

## Renderer

```text
version   ctx_oracle_v3.1_A002_record_id
file      finetune/context_renderer_v3.py
sha256    6b84ccf6c3b0868c4f73efbd5adcd236de1c35341e6d905a43bd69c45b197ab5
```

The hash is computed **externally**, over the finalized file; a renderer cannot contain its own final hash.

### Frozen rendering spec

```json
{
  "renderer_version": "ctx_oracle_v3.1_A002_record_id",
  "scalar_field_order": [
    "company",
    "category",
    "industry_group",
    "location",
    "address",
    "primary_facility_type",
    "ev_supply_chain_role",
    "primary_oems",
    "supplier_or_affiliation_type",
    "employment",
    "product_or_service",
    "ev_battery_relevant",
    "classification_method",
    "city",
    "county"
  ],
  "child_fact_order": [
    "processes",
    "services",
    "certifications"
  ],
  "labels": {
    "company": "Company",
    "category": "Category",
    "industry_group": "Industry group",
    "location": "Location",
    "address": "Address",
    "primary_facility_type": "Primary facility type",
    "ev_supply_chain_role": "EV supply chain role",
    "primary_oems": "Primary OEMs",
    "supplier_or_affiliation_type": "Supplier or affiliation type",
    "employment": "Employment",
    "product_or_service": "Product / service",
    "ev_battery_relevant": "EV / battery relevant",
    "classification_method": "Classification method",
    "city": "City",
    "county": "County",
    "processes": "Processes",
    "services": "Services",
    "certifications": "Certifications"
  },
  "label_separator": ": ",
  "line_separator": "\n",
  "term_separator": "; ",
  "null_render": "Not specified",
  "child_ordering": "Phase 5 canonical case-insensitive order (never SQLite row order)",
  "system_prompt": "You are answering questions about companies in the Georgia new-energy mobility supply chain. Use only the company record provided. If the record does not contain the answer, say so.",
  "context_heading": "Company record:",
  "question_heading": "Question:",
  "whitespace": "canonical values preserved verbatim; no trimming or collapsing",
  "duplicate_rendering": "multi-valued fields rendered exactly once, as child facts",
  "forbidden_in_context": [
    "certification_count",
    "graph_edges",
    "graph_id",
    "latitude",
    "longitude",
    "split",
    "split_group"
  ]
}
```

Multi-valued fields are rendered **exactly once**, as child-fact sections. The Phase 4 allowlist contains them, so the scalar projection explicitly excludes them rather than rendering the same evidence twice.

## Environment and tokenizer provenance

```text
environment path   .venv-v3  (repo-local, git-ignored, never committed)
python             3.12.3
transformers       5.14.1
tokenizers         0.22.2
huggingface_hub    1.28.0
jinja2             3.1.6
model/tokenizer    Qwen/Qwen2.5-14B-Instruct
revision           cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8
tokenizer class    Qwen2Tokenizer
tokenizer.json     c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539
load mode          local_files_only=True
```

The v2 repository's `.venv-ft` is deliberately **not** used: that path is the frozen v2 reference repository, and `CLAUDE.md` §7 forbids a runtime dependency on it. No tokenizer or revision was substituted.

## Context-budget equation

```text
tokenizer advertised max_model_length   131072   INFORMATIONAL ONLY — not used
model configured context                32768   config.json max_position_embeddings
evaluator max_seq_length                32768   frozen in Phase 6
--------------------------------------------------------------------------
usable_context = min(model, evaluator) = 32768
max_new_tokens (reserved)              = 1024
maximum input tokens                   = 31744

every accepted prompt satisfies:  input + 1024 <= 32768
```

The tokenizer advertising 131072 while the model supports 32768 is exactly the model/evaluator mismatch this assertion exists to surface. Generation tokens are reserved **before** a prompt is accepted; an over-budget prompt raises.

## Prompt-family measurements

| family | applicability | status | cases | min | median | p95 | max | +max_new | usable | margin | result |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `base_ctx_oracle` | factual probes only | **implemented & measured** | 615 | 204 | 241 | 288 | 324 | 1348 | 32768 | 31420 | PASS |

### What is validated now vs. later

**Validated now:**

- all 205 rendered row contexts (structural renderer fixtures)
- chat-template + system + instruction overhead: **60 tokens**
- worst-case renderer envelope (below)

**To be revalidated later:** every actual factual probe/question when it is generated. Those questions do not exist yet, so Phase 6 makes **no claim** that they are validated. Later probe generation must run every real prompt through this same budget checker.

```text
worst-case rendered context tokens   261
fixed template/system overhead       60
maximum input allowance              31744
remaining future question allowance  31423
```

## Worst-case rendered row

The true maximum under the frozen KB — not a smaller, cleaner example. No gold answer is exposed.

```text
largest rendered context   row_id 196  WIKA USA
                           261 context tokens
largest fixture prompt     row_id 196  WIKA USA
                           324 complete-prompt tokens
                           + 1024 reserved = 1348
remaining margin           31420 tokens
```

## Oracle retrieval is not answer leakage

The row is deliberately the correct one, so its raw evidence is **expected** to contain what a question asks for — `Employment: 500` is legitimate even when the eventual answer is `500`. Rejecting that would reject the baseline itself.

What is forbidden is a separate **target/evaluation artifact**. The gate scans for annotation markers, not raw values:

```text
  gold answer, gold_answer, expected answer, expected_answer, correct answer, correct_answer, gold sql, gold_sql
  answer_type, target_columns, probe_id, is_correct, correctness, evaluation label, eval_label, generated qa, generated_qa, train_kb_gold, train_dev_kb_gold, full_kb_gold
```

Also absent: `split`, `split_group`, `certification_count`, latitude, longitude, graph metadata, and every Phase 5 physical scoped-view name. No outside knowledge enriches the context.

## Truncation checks

**No silent truncation anywhere.** Tokenization runs without truncation, and a source scan of the Phase 6 code paths rejects `truncation=True`, `max_length=` slicing, `.truncate(`, token-id slicing and long literal clipping. An over-budget prompt raises a gate failure; it is never trimmed, and no row or field is dropped to make it fit.

Phase 7 separately owns removing the historical evaluator's `truncation=True, max_length=24576`; that migration is not performed here.

## Validation

| check | result | detail |
|---|---|---|
| `phase5_db_sha_unchanged` | PASS | 7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b |
| `phase2_3_4_hashes_unchanged` | PASS | canonical 42851c0a2e93… · split a59d673ac9ac… · kb_v3 2f13bc61212c… |
| `real_tokenizer_loaded_at_pinned_revision` | PASS | Qwen/Qwen2.5-14B-Instruct @ cf98f3b3bbb4… (Qwen2Tokenizer, local_files_only=True) |
| `tokenizer_json_sha_matches_expected` | PASS | c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539 |
| `real_chat_template_used` | PASS | tokenizer.chat_template applied via apply_chat_template |
| `advertised_limit_not_used_for_budget` | PASS | tokenizer advertises 131072; budget uses 32768 from config.json |
| `usable_context_equation` | PASS | min(32768, 32768) = 32768 |
| `max_input_tokens_reserves_generation` | PASS | 32768 - 1024 = 31744 |
| `all_205_rows_rendered` | PASS | 205 contexts |
| `all_fixture_prompts_within_budget` | PASS | 615 fixture prompts, all satisfying input + 1024 <= 32768 |
| `no_gold_answer_or_evaluation_artifacts` | PASS | no gold-answer/gold-SQL/generated-QA/answer_type/target_columns/correctness annotation in any context |
| `no_infrastructure_metadata_in_context` | PASS | split/split_group/certification_count/lat/long/graph absent |
| `no_physical_scoped_view_names_in_context` | PASS | none of 12 Phase 5 view names appear |
| `raw_kb_facts_preserved_in_context` | PASS | canonical values render verbatim; evidence that answers a question is expected in an oracle-context baseline and is NOT leakage |
| `zero_certification_rows_render_frozen_sentinel` | PASS | 34 row(s) render the frozen state; no certification fact manufactured |
| `multivalued_fields_rendered_exactly_once` | PASS | 0 row(s) rendering a multi-valued field more than once |
| `rendering_deterministic_in_process` | PASS | byte-identical on repeat render |
| `rendering_deterministic_across_process` | PASS | fresh interpreter reproduces byte-identical output |
| `explicit_scope_required` | PASS | None/unknown/case-variant/non-string all rejected |
| `cross_scope_row_request_rejected` | PASS | all 40 test rows rejected under scope='train_kb' |
| `in_scope_rows_still_render` | PASS | 148 train rows renderable under train_kb |
| `no_silent_truncation_in_phase6_paths` | PASS | no truncation=True / max_length slicing / clipping |

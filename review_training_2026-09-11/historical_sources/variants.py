"""The experiment matrix.

Each variant is one training recipe over the same 205 Excel rows, plus the two
no-training baselines that tell us whether fine-tuning was worth doing at all.

`answer_mode` decides how the eval harness turns a completion into an answer:
  "direct"  the completion *is* the answer.
  "sql"     the completion is a query; the executor produces the answer.
  "router"  the model first classifies the question, then answers through the
            backend that classification selects -- context, SQL, spatial SQL or
            the graph. Two generation passes per item.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-14B-Instruct"


@dataclass
class Variant:
    name: str
    description: str
    dataset: str | None          # None => no training (baseline)
    data_field: str = "messages" # "messages" (chat) or "text" (plain LM)
    answer_mode: str = "direct"  # "direct" | "sql"
    epochs: float = 3.0
    lr: float = 1e-4
    lora_r: int = 32
    lora_alpha: int = 64
    context_mode: str = "none"   # "none" | "full_table"  (baselines only)
    # Few-shot SQL exemplars prepended as chat turns before the real question.
    # Drawn from the structured *training* pool, which by construction excludes
    # the held-out operations -- so the novel query forms stay novel.
    few_shot: int = 0
    # Router variants only: the adapter to enable on the SQL-bearing routes.
    # None keeps the base model everywhere, which isolates how much of the
    # routed system's score is the routing itself rather than the fine-tune.
    sql_adapter: str | None = None
    tags: list[str] = field(default_factory=list)


VARIANTS: dict[str, Variant] = {
    # ---------------- baselines: no fine-tuning ----------------
    "base": Variant(
        name="base",
        description="Instruct model, closed book. Floor: what the model already knows about Georgia EV suppliers.",
        dataset=None,
        tags=["baseline"],
    ),
    "base_ctx": Variant(
        name="base_ctx",
        description="Instruct model with all 205 rows pasted into the prompt. The 'do nothing, just retrieve' ceiling.",
        dataset=None,
        context_mode="full_table",
        tags=["baseline", "rag"],
    ),
    "base_sql": Variant(
        name="base_sql",
        description="Instruct model, no training, prompted to emit SQL. Isolates how much of variant D is prompting vs tuning.",
        dataset=None,
        answer_mode="sql",
        tags=["baseline", "tools"],
    ),

    # ---------------- fine-tuning variants ----------------
    "A_cpt": Variant(
        name="A_cpt",
        description="Continued pretraining on raw row passages. Pure knowledge injection, no task format.",
        dataset="train_A_cpt.jsonl",
        data_field="text",
        epochs=4.0,
        lr=1e-4,
        tags=["finetune", "knowledge"],
    ),
    "B_facts": Variant(
        name="B_facts",
        description="SFT on cell-level fact QA. The classic 'teach it our data' recipe.",
        dataset="train_B_facts.jsonl",
        epochs=3.0,
        lr=1e-4,
        tags=["finetune", "knowledge"],
    ),
    "C_answers": Variant(
        name="C_answers",
        description="SFT on filter/aggregate questions with final answers, closed book. Tests whether reasoning can be trained in directly.",
        dataset="train_C_answers.jsonl",
        epochs=3.0,
        lr=1e-4,
        tags=["finetune", "reasoning"],
    ),
    "BC_facts_answers": Variant(
        name="BC_facts_answers",
        description="B + C together. The most generous closed-book recipe.",
        dataset="train_BC_facts_answers.jsonl",
        epochs=3.0,
        lr=1e-4,
        tags=["finetune", "knowledge", "reasoning"],
    ),
    "D_sql": Variant(
        name="D_sql",
        description="SFT on question -> SQLite query, executed externally. The model routes; the database computes.",
        dataset="train_D_sql.jsonl",
        answer_mode="sql",
        epochs=3.0,
        lr=1e-4,
        tags=["finetune", "tools"],
    ),
    "BD_facts_sql": Variant(
        name="BD_facts_sql",
        description="B + D. Facts in the weights for vocabulary grounding, SQL for anything that needs to be counted.",
        dataset="train_BD_facts_sql.jsonl",
        answer_mode="sql",
        epochs=3.0,
        lr=1e-4,
        tags=["finetune", "knowledge", "tools"],
    ),
    "base_sql_5shot": Variant(
        name="base_sql_5shot",
        description="Instruct model, no training, schema plus five worked question -> SQL examples. The other half of RQ3: base_sql answers 'does tuning beat schema prompting', this answers 'does it beat few-shot'.",
        dataset=None,
        answer_mode="sql",
        few_shot=5,
        tags=["baseline", "tools"],
    ),
    # ---------------- recursive-CTE dose-response (audit Phase 5) -------------
    # `D_sql` plus a fixed 25 county-proximity examples, k of which require
    # `WITH RECURSIVE`. Hyperparameters are copied from `D_sql` exactly and the
    # example count is identical across the three, so the dose is the only
    # variable. They answer RQ1 -- whether SQL-only training suppresses a
    # construct it never saw -- which `ERROR_ANALYSIS` can only observe.
    # Deliberately absent from REPORT_ORDER: they are one experiment among
    # themselves, not candidates for "best single variant".
    "D_sql_k0": Variant(
        name="D_sql_k0",
        description="D_sql + 25 county-proximity examples, none recursive. The dose-response control: same table and example count as k5/k25, zero exposure to WITH RECURSIVE.",
        dataset="train_D_sql_k0.jsonl",
        answer_mode="sql",
        epochs=3.0,
        lr=1e-4,
        tags=["finetune", "tools", "dose"],
    ),
    "D_sql_k5": Variant(
        name="D_sql_k5",
        description="D_sql + 25 county-proximity examples, 5 of them recursive. Low dose.",
        dataset="train_D_sql_k5.jsonl",
        answer_mode="sql",
        epochs=3.0,
        lr=1e-4,
        tags=["finetune", "tools", "dose"],
    ),
    "D_sql_k25": Variant(
        name="D_sql_k25",
        description="D_sql + 25 county-proximity examples, all recursive. High dose.",
        dataset="train_D_sql_k25.jsonl",
        answer_mode="sql",
        epochs=3.0,
        lr=1e-4,
        tags=["finetune", "tools", "dose"],
    ),
    # ---------------- routed systems: no training of their own ----------------
    # Not a tenth recipe. The capability breakdown shows no single variant wins
    # every skill, so these dispatch per question instead of picking one model.
    "router": Variant(
        name="router",
        description=(
            "Base model routes each question to context / SQL / spatial SQL / graph, "
            "then answers through that backend. No fine-tuning anywhere -- isolates "
            "what routing alone is worth."
        ),
        dataset=None,
        answer_mode="router",
        tags=["baseline", "router", "tools", "rag"],
    ),
    "router_ft": Variant(
        name="router_ft",
        description=(
            "Same routing, but the SQL-bearing routes run the BD_facts_sql adapter "
            "and the semantic route disables it. Intended as the best backend for "
            "every skill at once; measured across three seeds it ties BD_facts_sql "
            "rather than beating it."
        ),
        dataset=None,
        answer_mode="router",
        sql_adapter="BD_facts_sql",
        tags=["router", "tools", "rag", "finetune"],
    ),
}

# The order the report presents results in.
REPORT_ORDER = [
    "base",
    "A_cpt",
    "B_facts",
    "C_answers",
    "BC_facts_answers",
    "base_ctx",
    "base_sql",
    "base_sql_5shot",
    "D_sql",
    "BD_facts_sql",
    "router",
    "router_ft",
]

ROUTER_VARIANTS = ["router", "router_ft"]

# Everything the routed system is measured against. Derived by excluding the
# routers rather than by slicing REPORT_ORDER at a fixed index: the slice was
# `[:9]`, so inserting a variant anywhere above it would have silently dropped
# the last single variant out of "best individual variant" and pulled a router
# in.
SINGLE_VARIANTS = [v for v in REPORT_ORDER if v not in ROUTER_VARIANTS]

# Minimum set to answer today's questions if time is short.
CORE_RUN = ["base", "B_facts", "C_answers", "D_sql", "base_ctx"]


def reseeding_trains(name: str) -> bool:
    """Does changing the seed produce different *weights* for this variant?

    `dataset is None` alone is the wrong test and silently mismeasures
    `router_ft`. It trains nothing of its own, but it loads `BD_facts_sql`'s
    adapter from the per-seed adapter root, so seed 13 and seed 47 run genuinely
    different weights. Left as a "baseline" it would be sampled at temperature
    *and* handed a different adapter each seed, mixing decoding variance into
    training variance -- the one thing the seed sweep exists to keep apart.

    True  -> retrain (or reuse a per-seed adapter) and decode greedily.
    False -> no weights change; the only variance available is sampling.
    """
    variant = VARIANTS[name]
    return variant.dataset is not None or variant.sql_adapter is not None

"""Deterministic grading. No LLM judge.

Every question in this experiment has a mechanically-derived gold answer, so
grading is string/set/number comparison. That matters: an LLM judge would add
its own variance to exactly the recall-vs-reasoning gap we are trying to
measure, and it would be scored by a model with the same blind spots.

Three metrics, chosen to match the three answer shapes:

  value_match   fact recall -- is the gold cell value present in the answer?
  set_f1        list answers -- precision/recall over extracted company names.
  number_match  aggregates -- is the gold figure present, and the argmax entity?
"""
from __future__ import annotations

import re
import unicodedata

from finetune import kb

# ---------------------------------------------------------------------------
# normalization
# ---------------------------------------------------------------------------

_SUFFIXES = re.compile(
    r"\b(inc|llc|ltd|corp|corporation|co|company|usa|u\.s\.a|america|americas|"
    r"holding|holdings|group|gmbh|plc|lp|llp)\b\.?",
    re.IGNORECASE,
)
_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text))
    text = text.replace("&", " and ")
    text = _PUNCT.sub(" ", text.lower())
    return _WS.sub(" ", text).strip()


def norm_company(name: str) -> str:
    """Aggressive normalization for gazetteer matching: drop legal suffixes."""
    base = norm(name)
    base = _SUFFIXES.sub(" ", base)
    return _WS.sub(" ", base).strip()


# ---------------------------------------------------------------------------
# company gazetteer
# ---------------------------------------------------------------------------

class Gazetteer:
    """Finds known company names inside free-form answer text.

    Longest-first matching so 'Sewon America Inc.' wins over a bare 'Sewon',
    and so overlapping names do not double-count.

    Suffix-stripped keys are only registered when they stay unambiguous. Four
    pairs in this KB collide otherwise -- 'Ecoplastic America Corporation' and
    'Ecoplastic Corporation' both reduce to 'ecoplastic' -- and collapsing them
    would silently forgive a model that named the wrong one.
    """

    def __init__(self, names: list[str]):
        self.canonical: dict[str, str] = {}

        # full normalized name, always unambiguous enough to keep
        for n in names:
            key = norm(n)
            if key:
                self.canonical.setdefault(key, n)

        # suffix-stripped alias, only if exactly one company reduces to it
        stripped: dict[str, set[str]] = {}
        for n in names:
            key = norm_company(n)
            if key:
                stripped.setdefault(key, set()).add(n)
        for key, owners in stripped.items():
            if len(owners) == 1 and key not in self.canonical:
                self.canonical[key] = next(iter(owners))

        # match longest keys first
        self.keys = sorted(self.canonical, key=len, reverse=True)

    def extract(self, text: str, ignore: str = "") -> set[str]:
        """Company names asserted by ``text``.

        ``ignore`` is the question. Names handed to the model in the question
        carry no information -- echoing "Novelis Inc." back from "What locations
        does Novelis Inc. operate in?" is not evidence of recall -- so they are
        excluded from both sides of the comparison.
        """
        # Suffix-stripped keys are word-prefixes of their full form, so a single
        # suffix-preserving haystack serves both key families.
        haystack = f" {norm(text)} "
        found: set[str] = set()
        for key in self.keys:
            if key and f" {key} " in haystack:
                found.add(self.canonical[key])
                # blank the span so a shorter contained name is not also matched
                haystack = haystack.replace(f" {key} ", " \x00 ")
        if ignore:
            found -= self.extract(ignore)
        return found


_GAZ: Gazetteer | None = None


def gazetteer() -> Gazetteer:
    global _GAZ
    if _GAZ is None:
        _GAZ = Gazetteer(kb.load_kb()["company"].unique().tolist())
    return _GAZ


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------

_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> set[float]:
    out = set()
    for m in _NUM.finditer(str(text)):
        try:
            out.add(float(m.group(0).replace(",", "")))
        except ValueError:
            pass
    return out


def token_f1(pred: str, gold: str) -> float:
    p, g = norm(pred).split(), norm(gold).split()
    if not p or not g:
        return float(p == g)
    common = 0
    gcount: dict[str, int] = {}
    for t in g:
        gcount[t] = gcount.get(t, 0) + 1
    for t in p:
        if gcount.get(t, 0) > 0:
            gcount[t] -= 1
            common += 1
    if common == 0:
        return 0.0
    prec, rec = common / len(p), common / len(g)
    return 2 * prec * rec / (prec + rec)


def value_match(pred: str, gold: str, numeric: bool = False) -> bool:
    """Is the gold cell value asserted by the prediction?"""
    if numeric:
        gold_nums = numbers_in(gold)
        pred_nums = numbers_in(pred)
        return bool(gold_nums) and gold_nums.issubset(pred_nums)
    gold_n, pred_n = norm(gold), norm(pred)
    if gold_n and gold_n in pred_n:
        return True
    # multi-valued gold ("A; B"): every part must appear
    parts = [norm(p) for p in re.split(r"[;|]", gold) if norm(p)]
    if len(parts) > 1 and all(p in pred_n for p in parts):
        return True
    return token_f1(pred, gold) >= 0.85


def set_f1(pred_set: set[str], gold_set: set[str]) -> dict[str, float]:
    if not gold_set and not pred_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "exact_set": 1.0}
    if not gold_set or not pred_set:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "exact_set": 0.0}
    tp = len(pred_set & gold_set)
    prec = tp / len(pred_set)
    rec = tp / len(gold_set)
    f1 = 2 * prec * rec / (prec + rec) if tp else 0.0
    return {
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "exact_set": float(pred_set == gold_set),
    }


_COUNT_CLAIM = re.compile(
    r"\bthere\s+(?:is|are)\s+(?:only\s+)?(\d[\d,]*)\b|^\s*(\d[\d,]*)\s+(?:distinct|matching|result)",
    re.IGNORECASE | re.MULTILINE,
)


def count_claim(text: str) -> int | None:
    """The 'There are N companies...' assertion, if the answer makes one."""
    m = _COUNT_CLAIM.search(str(text))
    if not m:
        return None
    raw = m.group(1) or m.group(2)
    try:
        return int(raw.replace(",", ""))
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# per-probe grading
# ---------------------------------------------------------------------------

def grade_recall(pred: str, item: dict) -> dict:
    numeric = item["attr"] == "employment"
    ok = value_match(pred, item["gold_value"], numeric=numeric)
    return {"correct": float(ok), "token_f1": token_f1(pred, item["gold_value"])}


NUMERIC_FAMILIES = {"count", "sum", "groupby_argmax", "geo_sum", "cert_count", "cert_argmax",
                    "rel_count", "rel_degree_argmax"}
# Families whose answer names a winning entity plus a figure; both must be right.
ARGMAX_FAMILIES = {"groupby_argmax", "cert_argmax", "rel_degree_argmax"}


def grade_structured(pred: str, item: dict) -> dict:
    """Grade a generated filter/aggregate answer against its pandas gold."""
    gaz = gazetteer()
    gold_text = item["gold_answer"]
    question = item.get("question", "")
    family = item["family"]

    result: dict[str, float] = {}

    if family in NUMERIC_FAMILIES:
        gold_nums = numbers_in(gold_text)
        pred_nums = numbers_in(pred)
        # Prefer an explicit gold_number: when the gold text itself contains
        # digits that are not the figure (a certification like "IATF 16949"),
        # the largest-number heuristic picks the wrong one.
        if item.get("gold_number") is not None:
            key_num = float(item["gold_number"])
        else:
            key_num = max(gold_nums) if gold_nums else None
        result["number_correct"] = float(key_num is not None and key_num in pred_nums)
        if family in ARGMAX_FAMILIES:
            # the winning entity (a county/role, or a certification standard);
            # gold answer leads with it unless passed explicitly.
            entity = item.get("gold_entity") or gold_text.split(" has the highest")[0].strip()
            result["entity_correct"] = float(norm(entity) in norm(pred))
            # Require the figure only when the question asked for it. Most
            # `groupby_argmax` questions ask "which county has the highest total
            # employment?" and nothing more; demanding a number scored every
            # correct answer zero, which is what made `D_sql` look like it had
            # lost `GROUP BY` (12.5% against `base_sql`'s 75%) when both name
            # the right county ~93% of the time.
            #
            # Keyed off the question rather than off digits in the gold prose,
            # because the prose is full of digits that are not the figure --
            # `Tier 1`, `Tier 2/3` -- and the largest-number heuristic below
            # picks those up. That is the same trap `gold_number` exists to
            # avoid for certifications like `IATF 16949`.
            asks_for_value = any(s in question.lower()
                                 for s in (" and what is", "how many", "what is that"))
            result["correct"] = (
                result["number_correct"] * result["entity_correct"] if asks_for_value
                else result["entity_correct"]
            )
        else:
            result["correct"] = result["number_correct"]
        return result

    gold_set = gaz.extract(gold_text, ignore=question)
    pred_set = gaz.extract(pred, ignore=question)
    scores = set_f1(pred_set, gold_set)
    result.update(scores)
    result["correct"] = scores["exact_set"]
    result["n_gold"] = float(len(gold_set))
    result["n_pred"] = float(len(pred_set))

    claimed = count_claim(pred)
    if claimed is not None:
        result["count_claim_correct"] = float(claimed == len(gold_set))
        result["count_claim_matches_own_list"] = float(claimed == len(pred_set))
    return result


# ---------------------------------------------------------------------------
# result-set equivalence
# ---------------------------------------------------------------------------

# Audit Phase 1/3. Text grading scores the *rendering* of a query result, so a
# correct query written differently from gold can score wrong for reasons that
# have nothing to do with SQL. This compares what the two queries actually
# return.
#
# THE ARITY RULE, stated rather than left implicit in `sqlexec.render`:
#
#   A result of one row and two columns is NOT equal to a result of one row and
#   one column holding the concatenation of those two values.
#
# This is a decision, not a fact, and it is the load-bearing one. `location` is
# a single recorded value, `"Alpharetta, Forsyth County"`, that the SQL mirror
# splits across `city` and `county`. Under this rule `SELECT city, county`
# stays wrong for a question asking what that recorded value is, and the
# `HINT_ARMS.md` finding stands: naming the schema fact changes the query and
# not the score. Relaxing the rule would flip the descriptive-hint arm from
# 0.000 to near-ceiling and turn that finding into "the grader was measuring
# formatting". Both readings are defensible; this one is chosen because the
# question asks for one value and two columns do not reproduce it.
#
# What is normalized, because none of it is the thing under test:
#   - column *names* and aliases: position and value carry the meaning
#   - row order, unless gold's outermost query has an ORDER BY
#   - text case and surrounding whitespace; numeric strings vs numbers
# What is not:
#   - column count (the arity rule above)
#   - duplicate rows: SELECT and SELECT DISTINCT are a real difference

_ORDER_BY = re.compile(r"\border\s+by\b", re.IGNORECASE)


def _cell(value) -> object:
    """Normalize one cell so formatting differences do not read as errors."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 6)
    text = _WS.sub(" ", str(value)).strip()
    try:
        return round(float(text), 6)
    except ValueError:
        return text.casefold()


def result_set_match(pred_sql: str, gold_sql: str, db_path=None) -> dict:
    """Compare two queries by what they return, not by how it renders.

    Returns `rs_correct` alongside an `rs_status` that keeps execution failures
    distinguishable from wrong answers -- the audit asks for execution errors
    reported separately rather than folded into the wrong-answer count, because
    a query that does not run and a query that returns the wrong rows call for
    different fixes.
    """
    from finetune import sqlexec  # local: sqlexec imports geo, which imports kb

    kwargs = {"db_path": db_path} if db_path is not None else {}
    if not gold_sql:
        return {"rs_status": "no_gold"}
    try:
        gold_cols, gold_rows = sqlexec.run_sql(gold_sql, **kwargs)
    except sqlexec.SQLError as exc:
        # A broken gold query is a dataset bug, not a model error. Surfaced as
        # its own status so it cannot be silently counted against the model.
        return {"rs_status": "gold_error", "rs_detail": str(exc)}
    try:
        pred_cols, pred_rows = sqlexec.run_sql(pred_sql, **kwargs)
    except sqlexec.SQLError as exc:
        return {"rs_correct": 0.0, "rs_status": "pred_error", "rs_detail": str(exc)}

    if len(pred_cols) != len(gold_cols):
        return {"rs_correct": 0.0, "rs_status": "arity",
                "rs_detail": f"{len(pred_cols)} cols vs gold {len(gold_cols)}"}

    pred = [tuple(_cell(v) for v in row) for row in pred_rows]
    gold = [tuple(_cell(v) for v in row) for row in gold_rows]
    ordered = bool(_ORDER_BY.search(sqlexec.extract_sql(gold_sql)))
    same = pred == gold if ordered else sorted(pred, key=repr) == sorted(gold, key=repr)
    return {
        "rs_correct": float(same),
        "rs_status": "match" if same else "rows",
        "rs_ordered": float(ordered),
        "n_rows_pred": float(len(pred)),
        "n_rows_gold": float(len(gold)),
    }


def grade_human_42(pred: str, item: dict) -> dict:
    """Grade against the human-validated answer.

    Most questions are scored on the set of companies named. Four are scored on
    required facts instead -- see taxonomy.ANSWER_TYPE for why.
    """
    from finetune.taxonomy import (
        ATTRIBUTE, ENTITY_VALUE, REQUIRED_NUMBERS, REQUIRED_PHRASES, answer_type,
    )

    num = int(item["num"])
    kind = answer_type(num)
    question = item.get("question", "")
    pred_n = norm(pred)

    if kind in (ATTRIBUTE, ENTITY_VALUE):
        phrases = REQUIRED_PHRASES.get(num, [])
        numbers = REQUIRED_NUMBERS.get(num, [])
        pred_nums = numbers_in(pred)
        hits = [norm(p) in pred_n for p in phrases]
        num_hits = [n in pred_nums for n in numbers]
        total = len(hits) + len(num_hits)
        got = sum(hits) + sum(num_hits)
        recall = got / total if total else 0.0
        return {
            "correct": float(got == total),
            # keep the f1 column populated so the report tables stay comparable
            "f1": recall,
            "phrase_recall": recall,
            "n_gold": float(total),
            "n_pred": float(got),
        }

    gaz = gazetteer()
    gold_set = gaz.extract(item["gold_answer"], ignore=question)
    pred_set = gaz.extract(pred, ignore=question)
    scores = set_f1(pred_set, gold_set)

    result = dict(scores)
    result["n_gold"] = float(len(gold_set))
    result["n_pred"] = float(len(pred_set))
    result["correct"] = scores["exact_set"]

    gold_claim = count_claim(item["gold_answer"])
    pred_claim = count_claim(pred)
    if gold_claim is not None and pred_claim is not None:
        result["count_claim_correct"] = float(gold_claim == pred_claim)

    # Self-consistency: does the model's own stated count match its own list?
    # Only meaningful where extraction is demonstrably reliable for this answer
    # shape -- i.e. where the gold answer's own claim matches its own extracted
    # set. Q10-style answers name the OEM alongside each supplier, so extraction
    # legitimately exceeds the claim and the check would misfire.
    extraction_reliable = gold_claim is not None and gold_claim == len(gold_set)
    if pred_claim is not None and extraction_reliable:
        result["count_claim_matches_own_list"] = float(pred_claim == len(pred_set))

    # numeric questions (employment figures) also need the figures right
    gold_nums = numbers_in(item["gold_answer"]) - {float(gold_claim or -1)}
    if gold_nums:
        hit = len(gold_nums & numbers_in(pred))
        result["number_recall"] = hit / len(gold_nums)
    return result

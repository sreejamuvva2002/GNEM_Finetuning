"""Skill taxonomy for the 42 human-validated questions.

The whole experiment turns on separating *recall* from *reasoning*, so each
question is hand-tagged with the capability it actually exercises. Tags were
assigned by reading the question together with its human-validated answer.

    lookup           one named entity, read its attributes back.
                     Pure parametric recall -- no set logic, no arithmetic.

    filter_list      scan all 205 rows, apply a structured predicate, return
                     the *exhaustive* matching set. Needs complete recall AND
                     set closure ("did I miss anyone?"), which a closed-book
                     model cannot verify.

    aggregate        count / sum / group-by / argmax / top-k. Needs arithmetic
                     over a set the model must first recall correctly.

    semantic_filter  predicate over the free-text `product_service` column
                     ("produces copper foil", "battery recycling"). Needs
                     semantic judgement per row, then exhaustive set closure.
"""
from __future__ import annotations

LOOKUP = "lookup"
FILTER_LIST = "filter_list"
AGGREGATE = "aggregate"
SEMANTIC_FILTER = "semantic_filter"

# question number -> (skill, one-line note on what the question demands)
QUESTION_SKILLS: dict[int, tuple[str, str]] = {
    1: (FILTER_LIST, "category=Tier 1/2 -> role + product, 18 rows"),
    2: (FILTER_LIST, "role in {Battery Cell, Battery Pack} -> tier"),
    3: (FILTER_LIST, "role=Thermal Management -> primary_oems"),
    4: (FILTER_LIST, "role in {Power Electronics, Charging Infrastructure} -> employment"),
    5: (FILTER_LIST, "classification/category=OEM -> roles covered"),
    6: (LOOKUP, "Novelis Inc. -> locations + facility types"),
    7: (AGGREGATE, "county=Gwinnett, argmax(employment) -> company + role"),
    8: (AGGREGATE, "filter Tier 1, group by county, sum(employment), argmax"),
    9: (AGGREGATE, "group by county, sum(employment), argmax + value"),
    10: (FILTER_LIST, "role=Vehicle Assembly -> primary_oems"),
    11: (LOOKUP, "Sewon America Inc. -> products across sites"),
    12: (FILTER_LIST, "category=Tier 2/3 AND ev_relevant -> roles"),
    13: (FILTER_LIST, "primary_oems contains Rivian -> grouped by tier + role"),
    14: (SEMANTIC_FILTER, "role text mentions wiring harness -> primary_oems"),
    15: (FILTER_LIST, "Tier 2/3 AND industry=Electronic and Electrical Equipment"),
    16: (SEMANTIC_FILTER, "product mentions copper foil / electrodeposited"),
    17: (SEMANTIC_FILTER, "Tier 1/2 AND engineered plastics/polymers -- gold answer is EMPTY"),
    18: (SEMANTIC_FILTER, "product mentions DC-to-DC / capacitors / power electronics"),
    19: (SEMANTIC_FILTER, "product mentions powder coating -> tier"),
    20: (SEMANTIC_FILTER, "battery role or battery product AND Tier 1/2 -> OEMs"),
    21: (SEMANTIC_FILTER, "Tier 2/3 AND employment>300 AND General Automotive AND EV-transferable"),
    22: (FILTER_LIST, "Tier 2/3 AND industry=Chemicals and Allied Products -> products"),
    23: (AGGREGATE, "group by role, HAVING count(*)=1 -- 28 single-supplier roles"),
    24: (AGGREGATE, "battery roles with exactly one distinct OEM"),
    25: (AGGREGATE, "count(Hyundai Metaplant suppliers WHERE employment<200)"),
    26: (FILTER_LIST, "Tier 2/3 AND ev_relevant AND role=General Automotive"),
    27: (FILTER_LIST, "Tier 1/2 AND primary_oems='Multiple OEMs'"),
    28: (FILTER_LIST, "role in {Thermal Management, Power Electronics} AND employment<200"),
    29: (FILTER_LIST, "ev_relevant AND category in {OEM Footprint, OEM Supply Chain}"),
    30: (AGGREGATE, "order by employment desc limit 10, with dual-relevance predicate"),
    31: (SEMANTIC_FILTER, "Tier 2/3 AND product mentions lightweight aluminium/composite"),
    32: (SEMANTIC_FILTER, "product mentions high-voltage / DC-to-DC / inverter / motor controller"),
    33: (FILTER_LIST, "employment>1000 AND ev_battery_relevant=Indirect"),
    34: (AGGREGATE, "thermal management, order by employment desc limit 4, with values"),
    35: (SEMANTIC_FILTER, "product/role mentions thermal -> role + facility type"),
    36: (FILTER_LIST, "Tier 1/2 AND role=General Automotive"),
    37: (AGGREGATE, "count + employment distribution for Thermal Management"),
    38: (SEMANTIC_FILTER, "product mentions battery recycling / second-life"),
    39: (SEMANTIC_FILTER, "product/facility mentions R&D / prototyping"),
    40: (SEMANTIC_FILTER, "primary_oems spans traditional AND EV-native OEM"),
    41: (FILTER_LIST, "industry=Chemicals -> distinct locations"),
    42: (FILTER_LIST, "primary_facility_type=R&D -> distinct locations"),
}

# ---------------------------------------------------------------------------
# Answer shape -- decides which metric each question is scored with.
#
# Most questions want a set of companies, so set-F1 over extracted names is
# right. Six are not: two ask for attributes *of a named company* (the company
# is given in the question, so the company set is empty by construction) and
# two answer with a county plus a figure. Scoring those with set-F1 would give
# a model that says nothing a perfect score, since empty == empty.
# ---------------------------------------------------------------------------

ENTITY_SET = "entity_set"      # set-F1 over company names (the default)
ATTRIBUTE = "attribute"        # attributes of a company named in the question
ENTITY_VALUE = "entity_value"  # a non-company entity plus a figure

ANSWER_TYPE: dict[int, str] = {6: ATTRIBUTE, 11: ATTRIBUTE, 8: ENTITY_VALUE, 9: ENTITY_VALUE}

# Facts that must appear in the answer, verified against the KB rows.
# Q15 and Q17 are deliberately absent: their gold company set is *correctly*
# empty ("no companies match"), which makes them the hallucination test.
REQUIRED_PHRASES: dict[int, list[str]] = {
    6: ["Atlanta", "Fulton County", "Manufacturing Plant"],
    11: [
        "LaGrange",
        "Troup County",
        "Automotive aftermarket parts",
        "Motor vehicle engines and parts",
        "Fire truck bodies",
    ],
    8: ["Troup County"],
    9: ["Hall County"],
}

REQUIRED_NUMBERS: dict[int, list[float]] = {
    8: [2435],
    9: [314452],
}


def answer_type(num: int) -> str:
    return ANSWER_TYPE.get(num, ENTITY_SET)


# Which skills the closed-book hypothesis expects a fact-finetuned model to pass.
CLOSED_BOOK_EXPECTED_PASS = {LOOKUP}

SKILL_ORDER = [LOOKUP, FILTER_LIST, AGGREGATE, SEMANTIC_FILTER]


def skill_of(num: int) -> str:
    return QUESTION_SKILLS[num][0]


def skill_counts() -> dict[str, int]:
    counts = {s: 0 for s in SKILL_ORDER}
    for skill, _ in QUESTION_SKILLS.values():
        counts[skill] += 1
    return counts

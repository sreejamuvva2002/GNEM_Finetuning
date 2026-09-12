"""Conservative answer parsing, retaining parse failures separately from factual errors.

No substring-containment correctness: an answer containing the correct certification
plus unsupported certificates must fail exact-set accuracy. Accepted formats are
JSON values, plain values, semicolon/bullet lists and the frozen training wrappers.


A-002.2 -- two INDEPENDENTLY computed quantities
================================================

`output_contract_compliant`  Judged from the ORIGINAL response text and the frozen
                             contract for the question's answer_type alone. Gold is
                             never consulted, so a well-formed wrong answer is
                             contract-compliant and a correct answer in prose is not.

`semantically_correct`       Did the answer carry the recorded value, after the
                             bounded repair described below.

`strict_result_schema_accuracy` is reported as the CONJUNCTION of the two, matching
grade_v3's existing use of that field as a secondary accuracy metric (an answer that
is right but mis-shaped scores 1.0 task / 0.0 strict). Explicitly:

    strict_result_schema_accuracy = 1.0  iff  the response was contract-compliant
                                              AND matched gold with NO repair.

Both inputs to that conjunction are also reported separately in `metrics`, so the
two axes can always be recovered independently of each other.


The frozen contract (datasets_v3/PROMPT_TEMPLATES_A002.json, output_instructions)
--------------------------------------------------------------------------------
    scalar  "Return only one JSON string or number containing the recorded value."
    set     "Return only a JSON array containing every requested value."
    top_k   "Return only a JSON array of rows in the requested order."

A response is contract-compliant when, after removing surrounding whitespace only,
it is exactly one JSON document of the required Python type: `str`/`int`/`float`
for scalar (JSON `true`/`false`/`null` are not "a string or number"), `list` for
set and top_k. A fenced code block is NOT compliant -- the contract says return
only the value. Compliance is a property of the bytes the model produced; it is
never inferred from normalized answer equality.

The compliance check uses STRICT JSON. Python's `json` module accepts the
nonstandard constants `NaN`, `Infinity` and `-Infinity`, which RFC 8259 does not
allow and which are not "a recorded value" under any question type; they are
rejected wherever they appear, at the top level or nested inside an array. Note
that the JSON *string* `"NaN"` is a perfectly ordinary string and stays compliant.


Bounded semantic repair
-----------------------
Models frequently deliver the right value under one SURPLUS quoting layer, either
as valid JSON whose decoded content is itself quoted (`"\\"Tier 1\\""`) or as
invalid JSON with a doubled pair (`""Tier 1""`). That is an output-format defect,
not a knowledge defect.

  R1  surplus_quote_strip -- remove symmetric, EXPLICITLY PAIRED surrounding quote
      layers: `"` closes only `"`, and `“` closes only `”`. A mismatched
      pair is never stripped.
  R2  named_object_unwrap -- unwrap a one-key JSON object ONLY when its key names
      the requested attribute or target column.

Repair budget (R1), MAX_QUOTE_LAYERS = 2 total layers per value:

  * The budget is seeded by whether `parse()` already consumed a JSON layer for
    this response: a successful `json.loads` strips exactly one quoting layer, so
    it costs 1 of the 2.
  * A JSON SCALAR is one value, so it gets one budget. `"\"Tier 1\""` spends 1 on
    the json.loads and 1 on R1, reaching `Tier 1` exactly at the cap. `""Tier 1""`
    is invalid JSON, spends 0 on decoding and 2 on R1, and also reaches the cap.
    A third quoting layer is NOT repaired and stays incorrect.
  * ARRAY MEMBERS each get their own budget, seeded identically from the SAME
    response-level decode, because decoding the array decodes each of its string
    members by the same one layer. So `["\"A\""]` spends 1 (decode) + 1 (R1) per
    member, and a member quoted three deep stays incorrect.

Both repairs are strictly WIDENING: correctness is `strict_match or repaired_match`,
so a repair can never turn a previously correct answer incorrect. This is enforced
at runtime (`RepairInvariantError`) and regression-tested.

Precondition verified over the frozen corpus on 2026-09-12: 0 of 37,625 gold string
values and 0 of 205 canonical field values are wholly wrapped in double quotes, so
no legitimate recorded value can be damaged by R1.

Deliberately NOT normalised, and regression-tested to stay incorrect:
  * boolean surface forms (`true` / `False`) against recorded `Yes` / `No` -- the
    contract asks for the recorded value, and these are not it;
  * substring containment, extra set members, missing set members;
  * one-key objects whose key does not name the requested attribute.

Known limitation, unchanged here: `grade_answer` grades any non-`set` answer_type
through the scalar branch, so `top_k` and `multi_part` are not correctly graded on
the natural-language path. No development record uses them (they appear only in
sealed probes). Tracked in validation_v3/PRE_TRAINING_GATES_A002.md.
"""
import json,re,unicodedata
from grade_v3 import GradeResult,classify_prediction_text
VERSION='answer_parser_A002.2'

# Total surplus quoting layers R1 may remove per value, counting a successful
# json.loads as the first. Raising this is a protocol change, not a bug fix.
MAX_QUOTE_LAYERS=2

# Explicitly paired quote delimiters. A mismatched pair is never stripped.
_QUOTE_PAIRS={'"':'"','“':'”'}


class RepairInvariantError(AssertionError):
    """A bounded repair rejected an answer that was already strictly correct."""


class NonStandardJSONError(ValueError):
    """RFC 8259 has no NaN/Infinity/-Infinity literal; the contract check rejects them."""


def _reject_nonstandard_constant(literal):
    raise NonStandardJSONError(f'non-standard JSON constant {literal!r}')


def normalize(v):return ' '.join(unicodedata.normalize('NFKC',str(v)).casefold().split()).rstrip('.')


def output_contract_compliant(text,answer_type):
    """Does the ORIGINAL response obey the frozen contract for this answer_type?

    Computed from the response text alone -- gold is never consulted. Surrounding
    whitespace is tolerated; a fenced block or any surrounding prose is not.
    Strict JSON only: NaN/Infinity/-Infinity are refused at any depth.
    """
    if not isinstance(text,str):return False
    try:value=json.loads(text.strip(),parse_constant=_reject_nonstandard_constant)
    except (json.JSONDecodeError,ValueError):return False
    if answer_type=='scalar':
        return isinstance(value,str) or (isinstance(value,(int,float)) and not isinstance(value,bool))
    if answer_type in ('set','top_k'):
        return isinstance(value,list)
    return False


def _strip_one_quote_layer(value):
    """Remove exactly one EXPLICITLY PAIRED surrounding quote layer, or report none."""
    text=value.strip()
    if len(text)>=2 and _QUOTE_PAIRS.get(text[0])==text[-1]:
        return text[1:-1],True
    return value,False


def unquote_bounded(value,layers_already_spent=0):
    """Strip surplus quoting up to MAX_QUOTE_LAYERS per value. Returns (value,repaired)."""
    repaired=False
    spent=layers_already_spent
    while isinstance(value,str) and spent<MAX_QUOTE_LAYERS:
        stripped,removed=_strip_one_quote_layer(value)
        if not removed:break
        value=stripped;spent+=1;repaired=True
    return value,repaired


def _requested_keys(item):
    """Key names a one-key object may legitimately use for the requested value."""
    keys=[str(item['attribute'])] if item.get('attribute') else []
    keys.extend(str(c) for c in (item.get('target_columns') or ()))
    return {normalize(k) for k in keys if k}


def unwrap_named_object(value,item):
    """Unwrap {"<requested attribute or target column>": v} only. Returns (value,repaired)."""
    if isinstance(value,dict) and len(value)==1:
        (key,inner),=value.items()
        if normalize(key) in _requested_keys(item):return inner,True
    return value,False


def _json_layer_spent(text):
    """1 when parse() consumed a JSON decode for this response, else 0.

    This is the R1 budget seed, and is deliberately NOT the same question as
    output_contract_compliant: parse() strips a code fence first, accepts any JSON
    type, and uses Python's permissive decoder, so a fenced, wrongly typed, or
    NaN/Infinity-bearing response can still spend this layer. It must mirror
    parse() exactly -- it accounts for a decode that actually happened, whereas
    output_contract_compliant judges the response against the frozen contract.
    """
    value=text.strip()
    if value.startswith('```'):
        match=re.fullmatch(r'```(?:json)?\s*\n?(.*?)\n?```',value,re.S)
        value=match[1].strip() if match else value
    try:
        json.loads(value);return 1
    except json.JSONDecodeError:
        return 0


def parse(text,item):
    value=text.strip()
    if value.startswith('```'):
        match=re.fullmatch(r'```(?:json)?\s*\n?(.*?)\n?```',value,re.S)
        if not match:raise ValueError('Malformed fenced answer')
        value=match[1].strip()
    try:return json.loads(value)
    except json.JSONDecodeError:pass
    value=re.sub(r'^The answer is\s+','',value,flags=re.I)
    # Strip only known full training wrappers, not arbitrary prefixes containing gold.
    company=re.escape(item.get('company',''))
    wrappers=[r'^The companies are:\s*',r'^'+company+r"(?:'s)? (?:recorded processes are|recorded services are):\s*",
        r'^The dataset records these certifications for '+company+r':\s*']
    for wrapper in wrappers:
        value=re.sub(wrapper,'',value,flags=re.I)
    value=re.sub(r'\. This does not independently establish current validity or customer qualification\.$','',value)
    if item['answer_type']=='set':
        if re.fullmatch(r'(?:No companies match|No matching companies|None)[.!]?',value,re.I):return []
        parts=re.split(r';|\n\s*(?:[-*•]|\d+[.)])\s*',value)
        parts=[re.sub(r'^[-*•]\s*','',x.strip()).rstrip('.') for x in parts if x.strip()]
        return parts
    if item.get('attribute')=='employment':
        m=re.fullmatch(r'The dataset records employment of (\d+) for '+company+r'; its scope and date are not established here\.',value,re.I)
        if m:return m[1]
    wrappers={
      'category':(rf'{company} is classified in the ',r' category\.'),
      'industry_group':(rf'{company} belongs to the ',r' industry group\.'),
      'location':(rf'{company} is located at ',r'\.'),
      'address':(rf"{company}'s street address is ",r'\.'),
      'primary_facility_type':(rf"{company}'s primary facility type is ",r'\.'),
      'ev_supply_chain_role':(rf"{company}'s EV supply chain role is ",r'\.'),
      'primary_oems':(rf"{company}'s primary OEMs are recorded as ",r'\.'),
      'supplier_or_affiliation_type':(rf"{company}'s supplier or affiliation type is ",r'\.'),
      'product_or_service':(rf"{company}'s product or service is ",r'\.'),
      'ev_battery_relevant':(rf'EV or battery relevance for {company} is recorded as ',r'\.'),
      'classification_method':(rf'{company} was classified by ',r'\.')}
    if item.get('attribute') in wrappers:
        prefix,suffix=wrappers[item['attribute']];m=re.fullmatch(prefix+'(.+?)'+suffix,value,re.I|re.S)
        if m:return m[1]
    return value.rstrip('.')


def grade_answer(text,item,truncated=False):
    status=classify_prediction_text(text,stopped_at_max_new_tokens=truncated)
    if status:return GradeResult(status,0.,0.,'No valid parsed answer'),None
    # Format compliance is decided here, from the raw response and the frozen
    # contract only, before any parsing or comparison against gold.
    compliant=output_contract_compliant(text,item['answer_type'])
    try:pred=parse(text,item)
    except (ValueError,TypeError) as exc:
        return GradeResult('parse_failure',0.,0.,str(exc),
            {'output_contract_compliant':compliant,'format_repairs':[],
             'semantically_correct':False}),None
    gold=item['gold_value']
    if isinstance(gold,dict) and 'rows' in gold:
        if item['answer_type']=='scalar':gold=gold['rows'][0][0]
        elif len(gold['columns'])==1:gold=[r[0] for r in gold['rows']]
        else:return GradeResult('parse_failure',0.,0.,'Multi-column natural-language parser not implemented',
            {'output_contract_compliant':compliant,'format_repairs':[],
             'semantically_correct':False}),pred
    seed=_json_layer_spent(text)
    repairs=[]
    if item['answer_type']=='set':
        candidate,object_repaired=unwrap_named_object(pred,item)
        if object_repaired:repairs.append('named_object_unwrap')
        if not isinstance(candidate,list) or not isinstance(gold,list):
            return GradeResult('parse_failure',0.,0.,'Expected list',
                {'output_contract_compliant':compliant,'format_repairs':repairs,
                 'semantically_correct':False}),pred
        gold_set={normalize(v) for v in gold}
        strict_set={normalize(v) for v in candidate} if not object_repaired else None
        # Each member carries its own budget, seeded from the same response decode.
        members=[unquote_bounded(v,seed) if isinstance(v,str) else (v,False) for v in candidate]
        if any(r for _,r in members):repairs.append('surplus_quote_strip')
        repaired_set={normalize(v) for v,_ in members}
        strict_ok=strict_set is not None and strict_set==gold_set
        ok=strict_ok or repaired_set==gold_set
        scored=strict_set if strict_ok else repaired_set
        tp=len(scored&gold_set)
        precision=tp/len(scored) if scored else float(not gold_set)
        recall=tp/len(gold_set) if gold_set else float(not scored)
        metrics={'precision':precision,'recall':recall,
                 'f1':2*precision*recall/(precision+recall) if precision+recall else 0.,
                 'extra_values':sorted(scored-gold_set),'missing_values':sorted(gold_set-scored)}
    else:
        strict_ok=not isinstance(pred,(dict,list)) and normalize(pred)==normalize(gold)
        candidate,object_repaired=unwrap_named_object(pred,item)
        if object_repaired:repairs.append('named_object_unwrap')
        if isinstance(candidate,str):
            candidate,quote_repaired=unquote_bounded(candidate,seed)
            if quote_repaired:repairs.append('surplus_quote_strip')
        repaired_ok=not isinstance(candidate,(dict,list)) and normalize(candidate)==normalize(gold)
        ok=strict_ok or repaired_ok
        metrics={}
    if strict_ok and not ok:
        raise RepairInvariantError('bounded repair rejected a strictly correct answer')
    # Documented conjunction: right value, delivered in the contracted format,
    # with no repair required. Both inputs are reported separately below.
    unrepaired_match=bool(strict_ok and not repairs)
    strict_schema=float(compliant and unrepaired_match)
    metrics.update({'output_contract_compliant':bool(compliant),
                    'semantically_correct':bool(ok),
                    'matched_without_repair':unrepaired_match,
                    'format_repairs':repairs,
                    'json_layer_spent_by_parse':seed})
    detail=('Conservative normalized exact-value/set metric; free-form equivalents may '
            'require separate adjudication')
    if ok and repairs:
        detail=('Semantically correct after bounded output-format repair ('
                +', '.join(repairs)+'); reported separately from the strict output contract')
    elif ok and not compliant:
        detail=('Semantically correct but the response is not one JSON value of the '
                'contracted type; strict output-contract compliance fails')
    return GradeResult('correct' if ok else 'incorrect',float(ok),strict_schema,detail,metrics),pred

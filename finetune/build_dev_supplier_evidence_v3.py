"""Build source-bound analytical development drafts; no inference or training."""
import collections
import hashlib
import json
from pathlib import Path
import kb_v3 as K
import holdout_v3 as H
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'datasets_v3/dev_supplier_evidence_r1_draft_v3.jsonl'
MANIFEST=ROOT/'validation_v3/DEV_SUPPLIER_EVIDENCE_R1_DRAFT_MANIFEST.json'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    train={r.row_id for r in K.load_kb('train_kb')}
    dev=sorted((r for r in K.load_kb('train_dev_kb') if r.row_id not in train),key=lambda r:r.row_id)
    terms={r.row_id:set(H.terms(r.processes,'processes')) for r in dev}
    membership=collections.defaultdict(list)
    for r in dev:
        for term in terms[r.row_id]:membership[term].append(r)
    shared=sorted(t for t,rs in membership.items() if len({r.company for r in rs})>=2)
    if len(shared)<8:raise ValueError('Need eight shared recorded processes')
    items=[]
    risks=[
        ('capacity','Does the recorded employment establish that either matching candidate can absorb the other candidate\'s production volume?'),
        ('qualification','Does this evidence establish that the matching candidates are currently customer-qualified substitutes?'),
        ('compatibility','Does this evidence establish that their products are interchangeable without engineering changes?'),
        ('availability','Does this evidence establish that either matching candidate has spare capacity available this month?'),
        ('import_exposure','Does this evidence establish whether the matching candidates depend on imported inputs?'),
        ('sole_source','Does this evidence establish that losing one matching candidate would leave the customer with no alternative supplier?'),
        ('lead_time','Does this evidence establish which matching candidate could replace the other sooner?'),
        ('capacity_proxy','Would choosing the matching candidate with the larger recorded employment establish greater available production capacity?')]
    for index,term in enumerate(shared[:8]):
        matches=membership[term][:2]
        other=next(r for r in dev if term not in terms[r.row_id])
        selected=sorted(matches+[other],key=lambda r:r.row_id)
        evidence=[{'row_id':r.row_id,'company':r.company,'recorded_processes':r.processes,
                   'recorded_employment':r.employment} for r in selected]
        context=('These are bounded workbook observations, not independently verified current facts. '
                 'Rows do not by themselves establish distinct facilities.\n'+json.dumps(evidence,ensure_ascii=False,sort_keys=True))
        for kind in ('alternatives','vulnerability'):
            axis,risk=risks[index]
            question=(f'Within the supplied records only, identify candidates worth investigating for {term}. '
                      'Explain what supports including or not including each named company, and whether these records alone '
                      'establish that the candidates can replace one another.' if kind=='alternatives' else
                      f'Consider the supplied companies with recorded process {term}. {risk} '
                      'State what the records do support and the additional evidence needed.')
            unknowns=(['Product specifications and compatibility','Current customer qualification',
                       'Available capacity, required volume and delivery timing'] if kind=='alternatives' else {
                'capacity':['Required volume, utilization, equipment throughput and available capacity'],
                'qualification':['Current customer-specific qualification and applicable approvals'],
                'compatibility':['Part specifications, materials, tolerances and validation evidence'],
                'availability':['Current utilization, available equipment and delivery commitments'],
                'import_exposure':['Input origins, procurement dependencies and import shares'],
                'sole_source':['Customer sourcing relationships and complete qualified-alternative coverage'],
                'lead_time':['Current stock, qualification duration, production scheduling and logistics'],
                'capacity_proxy':['Comparable employment scope/date, process throughput and spare capacity']}[axis])
            items.append({'example_id':f'DEV_SUPPLIER_R1_{index+1:02d}_{kind}',
                'context_pair_id':f'DEV_SUPPLIER_R1_{index+1:02d}', 'kind':kind,
                'risk_axis':axis if kind=='vulnerability' else 'replaceability',
                'status':'draft_requires_human_rubric_review','track':'provided_evidence',
                'scope':'supplied_dev_records_only','question':question,'context':context,
                'context_sha256':hashlib.sha256(context.encode()).hexdigest(),
                'source_row_ids':[r.row_id for r in selected],'process_requirement':term,
                'fact_sheet':{'allowed_claims':evidence,
                    'supported_candidate_row_ids':[r.row_id for r in matches],
                    'not_supported_by_recorded_process_row_ids':[other.row_id],
                    'required_unknowns':unknowns,
                    'required_supported_partial_answer':'Identify both matching companies and their recorded process evidence.',
                    'prohibited_inferences':['Process overlap proves a qualified or interchangeable substitute.',
                        'Recorded employment measures available capacity.',
                        'Missing process evidence proves the company cannot perform it.',
                        'The bounded context is an exhaustive supplier census.',
                        'Recorded processes establish procurement origins, sole sourcing or delivery timing.']},
                'scoring':{'dimensions':['evidence_fidelity','constraint_handling','uncertainty','reasoning_completeness'],
                    'scale':[0,1,2],'clarification_quality':'not_applicable',
                    'critical_errors':['Unsupported decisive qualification, compatibility, capacity, import or sole-source claim'],
                    'blanket_refusal':'Cannot receive full completeness credit without the supported partial answer.',
                    'method':'human_review_required_no_regex_semantic_scoring'},
                'training_eligible':False,'checkpoint_selection':False})
    return items


def main():
    if OUT.exists() or MANIFEST.exists():raise RuntimeError('Preserve draft version')
    items=build()
    assert len(items)==16 and len({i['example_id'] for i in items})==16
    OUT.write_text(''.join(json.dumps(i,ensure_ascii=False)+'\n' for i in items))
    MANIFEST.write_text(json.dumps({'version':'dev_supplier_evidence_r1_draft','items':16,
        'alternative_items':8,'vulnerability_items':8,'status':'draft_not_adjudicated',
        'selection':'First eight lexically sorted process terms shared by two dev companies; first two matches and first dev nonmatch by row ID.',
        'inference_performed':False,'fields':['company','row_id','processes','employment'],
        'sha256':{str(p.relative_to(ROOT)):sha(p) for p in [OUT,Path(__file__),K.CANONICAL,K.SPLIT_CSV,ROOT/'finetune/holdout_v3.py']},
        'limitations':['Shared contexts and source rows correlate items.','Process overlap is only a screening proxy.','Provided evidence, not memory recall.','No certification/process composition or held-out grouping/ranking target.','Human rubric review and unchanged-base baseline still pending.']},indent=2)+'\n')
    print('Created 8 alternative and 8 vulnerability draft items.')

if __name__=='__main__':main()

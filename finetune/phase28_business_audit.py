"""Construct a reviewable Q42 audit. Never grant human approval or run models."""
import csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import sqlexec_v3 as X
import holdout_v3 as H
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'datasets_v3'

def select(where,cols='company',distinct=True):
    return f'SELECT {"DISTINCT " if distinct else ""}{cols} FROM companies WHERE {where} ORDER BY company'
def contains(fields,terms):
    return '('+' OR '.join(f"LOWER({f}) LIKE '%{t.lower()}%'" for f in fields for t in terms)+')'
ROLE='ev_supply_chain_role';PROD='product_or_service'
thermal=contains([ROLE,PROD],['thermal'])
battery=contains([ROLE,PROD],['battery'])
relevant="ev_battery_relevant IN ('Yes','Indirect')"
primary="ev_battery_relevant='Yes'"
def childmatch(terms):
    return '('+' OR '.join(f"company IN (SELECT company FROM {table} WHERE {contains([col],terms)})" for table,col in [('processes','process'),('services','service')])+')'

def main():
    source=ROOT/'validation_v3/resumption/V2_Q42_SOURCE.jsonl'
    old=[json.loads(l) for l in source.read_text().splitlines()]
    assert len(old)==42
    queries={
      1:select("category='Tier 1/2'",f'company,{ROLE},{PROD}'),
      2:select(f"{ROLE} IN ('Battery Cell','Battery Pack')",f'company,category,{ROLE}'),
      3:select(f"{ROLE}='Thermal Management'",'company,primary_oems'),
      4:select(contains([ROLE],['power electronics','charging infrastructure']),f'company,{ROLE},employment'),
      5:select("classification_method='Direct Manufacturer'",f'company,{ROLE}'),
      6:select("company='Novelis Inc.'",'row_id,company,location,primary_facility_type',False),
      7:"SELECT company, employment, ev_supply_chain_role FROM companies WHERE county='Gwinnett County' ORDER BY employment DESC, company, row_id LIMIT 1",
      8:"SELECT county FROM companies WHERE category='Tier 1' AND county IS NOT NULL GROUP BY county ORDER BY SUM(employment) DESC, county LIMIT 1",
      9:"SELECT county, SUM(employment) AS recorded_total FROM companies WHERE county IS NOT NULL GROUP BY county ORDER BY recorded_total DESC, county LIMIT 1",
      10:select(f"{ROLE}='Vehicle Assembly'",'row_id,company,primary_oems',False),
      11:select("company='Sewon America Inc.'",f'row_id,company,location,{PROD}',False),
      12:select("category='Tier 2/3' AND "+primary,f'company,{ROLE}'),
      13:select("primary_oems LIKE '%Rivian%'",f'company,category,{ROLE},primary_oems'),
      14:select(contains([ROLE],['wiring harness']),'company,primary_oems'),
      15:select("category='Tier 2/3' AND industry_group='Electronic and Other Electrical Equipment and Components'",f'company,{PROD}'),
      16:select(contains([PROD],['copper foil','electrodeposited']),f'company,{PROD}'),
      17:select("category='Tier 1/2' AND ("+contains([PROD],['plastic','polymer','composite'])+' OR '+childmatch(['plastic','polymer','composite'])+')',f'company,{PROD}'),
      18:select(contains([PROD,ROLE],['dc-to-dc','capacitor','power electronics']),'company,category'),
      19:select('('+contains([PROD],['powder coat'])+' OR '+childmatch(['powder coat'])+')','company,category'),
      20:select("category='Tier 1/2' AND "+battery,'company,primary_oems'),
      21:select("category='Tier 2/3' AND employment>300 AND ev_supply_chain_role='General Automotive'",f'company,employment,{PROD}'),
      22:select("category='Tier 2/3' AND industry_group='Chemicals and Allied Products'",f'company,{PROD}'),
      23:"SELECT ev_supply_chain_role, COUNT(DISTINCT company) AS recorded_companies FROM companies GROUP BY ev_supply_chain_role HAVING COUNT(DISTINCT company)=1 ORDER BY ev_supply_chain_role",
      24:None,25:None,
      26:select("category='Tier 2/3' AND "+primary+" AND ev_supply_chain_role='General Automotive'"),
      27:select("category='Tier 1/2' AND primary_oems='Multiple OEMs'"),
      28:select('('+contains([ROLE],['thermal management','power electronics'])+') AND employment<200',f'company,employment,{ROLE}'),
      29:select(relevant+" AND category IN ('OEM (Footprint)','OEM Supply Chain')",'company,category'),
      30:"SELECT company, employment FROM companies WHERE ev_supply_chain_role='General Automotive' AND "+relevant+" ORDER BY employment DESC, company, row_id LIMIT 10",
      31:select("category='Tier 2/3' AND "+relevant+' AND '+contains([PROD],['aluminum','aluminium','composite']),f'company,{PROD},ev_battery_relevant'),
      32:select(contains([PROD],['high-voltage','dc-to-dc','inverter','motor controller']),f'company,{PROD}'),
      33:select("employment>1000 AND ev_battery_relevant='Indirect'",'company,employment'),
      34:'SELECT company, employment FROM companies WHERE '+thermal+' ORDER BY employment DESC, company, row_id LIMIT 4',
      35:select('('+thermal+' OR '+childmatch(['thermal'])+')',f'company,{ROLE},primary_facility_type'),
      36:select("category='Tier 1/2' AND ev_supply_chain_role='General Automotive'"),
      37:{'count':'SELECT COUNT(DISTINCT company) AS n FROM companies WHERE '+thermal,
          'employment':select(thermal,'row_id,company,employment',False)},
      38:select(contains([PROD],['recycl','second-life']),f'company,{PROD}'),
      39:select('('+contains([PROD,'primary_facility_type'],['r&d','research','prototyp'])+' OR '+childmatch(['research','prototyp'])+')',f'company,{PROD},primary_facility_type'),
      40:select("primary_oems LIKE '%Rivian%' AND (primary_oems LIKE '%Hyundai%' OR primary_oems LIKE '%Kia%')",'company,primary_oems'),
      41:select("industry_group='Chemicals and Allied Products'",'company,location'),
      42:select(contains(['primary_facility_type'],['r&d','research']),'company,location,primary_facility_type')}
    ambiguous={3,4,6,7,8,9,10,11,12,13,15,16,17,18,20,21,23,24,25,27,28,29,30,31,33,34,35,37,38,39,40,41,42}
    records=[];audit=[]
    for oldrow in old:
        n=oldrow['num'];sql=queries[n]; gold={};parts=[]
        if sql is not None:
            statements=sql if isinstance(sql,dict) else {'answer':sql}
            for part,stmt in statements.items():
                result=X.run_sql(stmt,'full_kb',db_path=OUT/'gnem_v3.sqlite')
                gold[part]={'columns':list(result.columns),'rows':[list(r) for r in result.rows]}
                parts.append({'part_id':part,'answer_type':'scalar' if part=='count' or n==8 else ('top_k' if n in {7,9,30,34} else 'set'),'target_columns':list(result.columns)})
        notes=['Source records are not independent verification of current operations or Georgia-only production.']
        if n in {7,8,9,25,28,30,33,34,37}:notes.append('Employment scope/date and conflicting duplicate observations prevent a defensible company-level or county workforce/capacity total; SQL output is only a record-level diagnostic.')
        if n in {6,10,11}:notes.append('Repeated rows do not prove distinct operational sites; preserve row attribution.')
        if n in {13,15,16,17,18,20,21,23,24,25,27,28,30,31,33,37,38,39,40,41,42}:notes.append('Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.')
        if n in {17,19,35,39}:notes.append('Process/service membership is included; keyword matching is an explicit candidate definition, not validated engineering suitability.')
        if n==5:notes.append('Use Classification Method = Direct Manufacturer; the old answer substituted Category = OEM.')
        if n==29:notes.append('Canonical category is OEM (Footprint); Yes and Indirect are included in this proposed interpretation.')
        if n in {24,25}:notes.append('The workbook lacks verified sole-source or Hyundai Metaplant-specific supplier links; no numerical or named-supplier conclusion is supported.')
        row={'example_id':f'Q{n:02d}','question':oldrow['question'],'family':'business_42','scope':'full_kb',
             'gold_sql':sql,'gold_value':gold if sql is not None else 'Insufficient evidence in the supplied dataset.',
             'answer_type':'multi_part' if isinstance(sql,dict) else (parts[0]['answer_type'] if parts else 'scalar'),
             'target_columns':list(dict.fromkeys(c for p in parts for c in p['target_columns'])) or ['evidence'],
             'parts':parts if isinstance(sql,dict) else [],'primary_eligible_proposal':n not in ambiguous,
             'human_approval':'pending','interpretation_notes':notes,'old_gold_answer':oldrow['gold_answer']}
        records.append(row)
        audit.append({'question_id':row['example_id'],'question':row['question'],'old_gold':oldrow['gold_answer'],
           'new_gold':json.dumps(row['gold_value'],ensure_ascii=False),'sql':json.dumps(sql),
           'primary_eligible_proposal':row['primary_eligible_proposal'],'human_approval':'pending',
           'ambiguity_note':' '.join(notes),'numeric_change':'Not mechanically comparable to unstructured old prose; inspect old/new gold side by side',
           'companies_added_removed':'Old prose is not a reliable structured entity list; inspect exact new rows against old gold'})
    (OUT/'probe_42_v3.jsonl').write_text(''.join(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in records))
    csvpath=ROOT/'validation_v3/PROBE_42_AUDIT_v3.csv'
    with csvpath.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
    lines=['# Q42 benchmark review — approval pending','','All 42 questions retain their original wording. Each proposed oracle is executed against the V3 database. Ambiguous business conclusions are proposed as diagnostic-only; no model predictions or scores exist.','',
           'Approval is required by README Phase 28 before full training. The attached CSV contains all old golds, new results and exact SQL. Numerical/company deltas are not certified because old gold is unstructured prose.','']
    for r in records:
        lines += [f"## {r['example_id']}: {r['question']}",'',f"Proposed primary eligibility: {r['primary_eligible_proposal']}. Approval: pending.",'',' '.join(r['interpretation_notes']),'','```json',json.dumps(r['gold_value'],ensure_ascii=False,indent=2),'```','']
    (ROOT/'validation_v3/Q42_REVIEW_A002.md').write_text('\n'.join(lines))
    print('Constructed 42 review entries; human approval and detailed semantic adjudication remain pending. No scores produced.')
if __name__=='__main__':main()

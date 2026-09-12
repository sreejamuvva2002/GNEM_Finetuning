"""Read-only review of source artifacts; writes evidence only beside this script."""
from pathlib import Path
import ast, collections, csv, hashlib, io, json, re, sqlite3, subprocess, sys, zipfile
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'finetune'))
def sha(b): return hashlib.sha256(b).hexdigest()
def jl(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
report = {}
prior = (ROOT / 'REPOSITORY_REVIEW_2026-09-11.md').read_text()
old = {p:h for p,h in re.findall(r'\| \[[^\]]+\]\(([^)]+)\) \|[^|]+\| `([0-9a-f]{12})`', prior)}
files = []
for p in sorted(ROOT.rglob('*')):
    rel = p.relative_to(ROOT)
    if any(x in ('.git', '.venv-v3', '__pycache__') for x in rel.parts) or rel.parts[0] == OUT.name or not p.is_file(): continue
    b = p.read_bytes(); item = {'path':str(rel), 'bytes':len(b), 'sha256':sha(b)}
    if str(rel) in old: item['prior_review_hash_matches'] = item['sha256'].startswith(old[str(rel)])
    if p.suffix in ('.py','.json','.jsonl','.csv','.md','.txt','.jinja','.log','.lock') or p.name=='.gitignore':
        s = b.decode('utf-8'); item['lines'] = len(s.splitlines())
        if p.suffix=='.py':
            tree=ast.parse(s); item['functions']=[n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        elif p.suffix=='.json': json.loads(s); item['parsed']='JSON'
        elif p.suffix=='.jsonl': item['records']=len([json.loads(x) for x in s.splitlines() if x.strip()])
        elif p.suffix=='.csv': item['records']=len(list(csv.DictReader(io.StringIO(s))))
    files.append(item)
report['inventory']={'files':len(files),'prior_entries':len(old),'prior_matches':sum(x.get('prior_review_hash_matches',False) for x in files),'prior_mismatches':[x['path'] for x in files if x.get('prior_review_hash_matches') is False], 'prior_missing':[x for x in old if not (ROOT/x).exists()]}
manifest=json.loads((ROOT/'review_training_2026-09-11/AUDIT_MANIFEST.json').read_text())
report['v2_evidence_hash_verification']={'files':len(manifest['files']),'mismatches':[p for p,v in manifest['files'].items() if sha((ROOT/'review_training_2026-09-11'/p).read_bytes())!=v['sha256']]}
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
workbook=ROOT/'kb/GNEM_Final_Combined_Dataset.xlsx'
with zipfile.ZipFile(workbook) as z:
    names=z.namelist(); strings=[]
    if 'xl/sharedStrings.xml' in names:
        strings=[''.join(e.itertext()) for e in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
    wb=ET.fromstring(z.read('xl/workbook.xml'))
    rels={e.attrib['Id']:e.attrib['Target'] for e in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    sheets=[]; main=[]; rawcells=[]
    for sh in wb.find('s:sheets',ns):
        rid=sh.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']; target=rels[rid]
        member=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        root=ET.fromstring(z.read(member)); entries=[]
        for c in root.findall('.//s:sheetData/s:row/s:c',ns):
            t=c.attrib.get('t'); v=c.find('s:v',ns); val=None
            if t=='inlineStr': val=''.join(c.find('s:is',ns).itertext())
            elif v is not None:
                val=v.text
                if t=='s': val=strings[int(val)]
                elif t not in ('str','e'):
                    try: val=int(val)
                    except ValueError: val=float(val)
            f=c.find('s:f',ns)
            if val is not None or f is not None:
                entries.append({'cell':c.attrib['r'],'value':val,'type':t,'style':c.attrib.get('s'),'formula':f.text if f is not None else None})
        sheets.append({'name':sh.attrib['name'],'state':sh.attrib.get('state','visible'),'value_cells':len(entries),'formula_count':sum(e['formula'] is not None for e in entries),'hidden_rows':len(root.findall('.//s:row[@hidden="1"]',ns)),'hyperlinks':len(root.findall('.//s:hyperlink',ns))})
        rawcells.extend({'sheet':sh.attrib['name'],**e} for e in entries)
        if sh.attrib['name']=='GNEM Combined':
            grid={e['cell']:e['value'] for e in entries}
            headers=[grid.get(f'{chr(65+i)}1') for i in range(18)]
            main=[{h:grid.get(f'{chr(65+i)}{r}') for i,h in enumerate(headers)} for r in range(2,207)]
    report['workbook']={'sha256':sha(workbook.read_bytes()),'matches_frozen_source':sha(workbook.read_bytes())==json.loads((ROOT/'datasets_v3/SOURCE_MANIFEST_v3.json').read_text())['source_workbook']['sha256'],'zip_members':names,'sheets':sheets,'headers':headers,'records':len(main),'exact_names':len({r['Company'].strip() for r in main}),'comments_or_external_or_embeddings':[n for n in names if any(v in n.lower() for v in ['comment','externallink','embedding'])]}
(OUT/'workbook_cells.json').write_text(json.dumps(rawcells,indent=2,ensure_ascii=False)+'\n')
canonical=jl(ROOT/'datasets_v3/canonical_records_v3.jsonl')
# Extract declared source mapping without importing openpyxl-dependent generator.
tree=ast.parse((ROOT/'finetune/phase2_clean_records.py').read_text())
mapping=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='COLUMN_TO_FIELD' for t in n.targets))
changes=[]; by_id={r['row_id']:r for r in canonical}; columnstats=[]
for src, field in mapping:
    changed=[]
    for row in main:
        rid=row['Record No.']; a=row[src]; b=by_id[rid][field]
        if a!=b: changed.append({'row_id':rid,'source_column':src,'field':field,'raw':a,'canonical':b})
    changes+=changed
    columnstats.append({'source_column':src,'field':field,'rows':len(main),'source_nonblank':sum(r[src] is not None and str(r[src]).strip()!='' for r in main),'canonical_changed':len(changed)})
clean_audit=list(csv.DictReader((ROOT/'validation_v3/CLEANING_AUDIT_v3.csv').open()))
logged={(int(r['row_id']),r['field']) for r in clean_audit}
report['cell_preservation']={'compared_cells':len(main)*len(mapping),'canonical_rows':len(canonical),'canonical_fields':len(canonical[0]),'row_ids_match':{r['Record No.'] for r in main}==set(by_id),'changed_cells':len(changes),'unlogged_changes':[c for c in changes if (c['row_id'],c['field']) not in logged],'columns':columnstats}
(OUT/'cell_changes.json').write_text(json.dumps(changes,indent=2,ensure_ascii=False)+'\n')
with sqlite3.connect(f'file:{ROOT}/datasets_v3/gnem_v3.sqlite?mode=ro',uri=True) as con:
    con.row_factory=sqlite3.Row
    report['database']={'integrity':con.execute('PRAGMA integrity_check').fetchone()[0], 'tables':{r[0]:{'columns':[x[1] for x in con.execute(f'PRAGMA table_info("{r[0]}")')], 'rows':con.execute(f'SELECT COUNT(*) FROM "{r[0]}"').fetchone()[0]} for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}}
import kb_v3 as KB, holdout_v3 as H
from sqlexec_v3 import run_sql, _strip_sql_noise
report['scopes']={s:{'rows':len(KB.load_kb(s)),'exact_names':len({r.company for r in KB.load_kb(s)})} for s in KB.KB_SCOPES}
report['model_fields']={'included':list(KB.MODEL_FACING_FIELDS),'excluded_source_fields':[f for _,f in mapping if f not in KB.MODEL_FACING_FIELDS]}
import phase11_build_b_facts as B
reg,held,train,items,skips,conflicts=B.build()
report['factual_generation']={'examples':len(items),'skip_reasons':dict(skips),'conflicts_all_splits':len(conflicts),'generated_matches_current':items==jl(ROOT/'datasets_v3/train_B_facts_v3.jsonl'),'attributes':dict(collections.Counter(x['attribute'] for x in items))}
pool=jl(ROOT/'datasets_v3/STRUCTURED_TASK_POOL_v3.jsonl'); mismatches=[]
for t in pool:
    r=run_sql(t['gold_sql'],'train_kb',db_path=ROOT/'datasets_v3/gnem_v3.sqlite')
    if list(r.columns)!=t['train_kb_gold']['columns'] or [list(x) for x in r.rows]!=t['train_kb_gold']['rows']: mismatches.append(t['task_id'])
report['pool_train_gold']={'executed':len(pool),'mismatches':mismatches}
report['training']={}
for p in sorted((ROOT/'datasets_v3').glob('train_*.jsonl')):
    data=jl(p); texts=[m['content'] for x in data for m in x.get('messages',[])]+[x['text'] for x in data if 'text' in x]
    # registry scanner is checked separately if its API changes.
    report['training'][p.name]={'examples':len(data),'message_counts':dict(collections.Counter(len(x.get('messages',[])) for x in data)),'answer_types':dict(collections.Counter(x.get('answer_type','not_declared') for x in data)),'duplicate_example_ids':len(data)-len({x.get('example_id',x.get('row_id')) for x in data})}
D=jl(ROOT/'datasets_v3/train_D_sql_v3.jsonl')
clean=[re.sub(r"'(?:''|[^'])*'",' ',_strip_sql_noise(x['messages'][-1]['content'])) for x in D]
report['D_operations']={op:sum(bool(re.search(r'\b'+op+r'\b',s,re.I)) for s in clean) for op in ['COUNT','SUM','AVG','MIN','MAX','GROUP BY','HAVING','LIMIT','OR','NOT','WITH','UNION']}
report['join_arity_mismatch']=sum(len(re.findall(r'\bJOIN\b',s,re.I))!=x['join_arity'] for x,s in zip(D,clean))
report['revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
(OUT/'file_inventory.json').write_text(json.dumps(files,indent=2)+'\n')
(OUT/'audit_results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('workbook','training','database','cell_preservation','model_fields')},indent=2))
print(json.dumps({'workbook':{k:v for k,v in report['workbook'].items() if k!='zip_members'},'cell_preservation':report['cell_preservation'],'database':report['database']},indent=2))

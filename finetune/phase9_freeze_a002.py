"""Freeze/check the user-authorized A-002 registry without rewriting V3.1 approval."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import holdout_v3 as H

def encoded(value):
    return json.dumps(value, indent=2, sort_keys=True) + '\n'

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    data=H.recompute_registry_dict()
    assert data == H.recompute_registry_dict(), 'Non-deterministic registry'
    assert all(not v['selected'] and v['train_rows_lost']==0 for v in data['value_holdouts'].values())
    old=json.loads((H.ROOT/'datasets_v3/HOLDOUT_REGISTRY_v3.json').read_text())
    for section in ('entity_holdouts','operation_holdouts','composition_holdouts'):
        assert data[section]==old[section], f'Unapproved holdout change: {section}'
    text=encoded(data)
    candidate=H._load_and_verify_candidate(text)
    H.assert_value_scan_verified(H.scan_strings(['ISO 9001; processes; services'],candidate))
    assert H.scan_operations(['SELECT county, COUNT(*) FROM companies GROUP/**/BY county'],candidate)['total_exposures']==1
    assert H.scan_compositions([['processes','certifications']],candidate)['composition_violations']>0
    for mutate in ('value','input','version'):
        bad=json.loads(text)
        if mutate=='value': bad['value_holdouts']['processes']['selected']=['INJECTED']
        elif mutate=='input': bad['frozen_inputs']['datasets_v3/canonical_records_v3.jsonl']='0'*64
        else: bad['policy_version']='stale'
        try: H._load_and_verify_candidate(encoded(bad))
        except H.HoldoutError: pass
        else: raise AssertionError(f'Mutation accepted: {mutate}')
    anchor={'approved_registry_sha256':candidate.sha256(),
            'approved_commit':'8e7196e0e58d6ebcb35d7a14944146039f4c912f',
            'approved_date':'2026-09-11',
            'authorization_basis':'User explicitly requested full-field original V3 and continuing all phases',
            'commit_semantics':'Historical base at authorization; not approval of a new commit',
            'validation':'Agent-run regression checks; no independent human approval claimed',
            'policy_code_sha256':H.sha256_file(Path(H.__file__)),
            'amendment_sha256':H.sha256_file(H.ROOT/'PROTOCOL_A002_FULL_FIELD.md')}
    ledger_path=H.ROOT/'datasets_v3/FACT_EXPOSURE_LEDGER_v3.json'
    if args.check:
        assert H.REGISTRY.read_text()==text
        assert json.loads(H.PHASE9_APPROVAL.read_text())==anchor
        assert json.loads(ledger_path.read_text())['registry_sha256']==candidate.sha256()
    else:
        if H.REGISTRY.exists() and H.REGISTRY.read_text()!=text:
            raise RuntimeError('Refusing to overwrite different frozen registry; version an amendment')
        H.REGISTRY.write_text(text)
        H.PHASE9_APPROVAL.write_text(encoded(anchor))
        # Later generators update arm evidence. Re-running freeze cannot reset it.
        if not ledger_path.exists() or json.loads(ledger_path.read_text()).get('registry_sha256')!=candidate.sha256():
            ledger={'ledger':'FACT_EXPOSURE_LEDGER_A002','policy_version':H.POLICY_VERSION,
                'registry_sha256':candidate.sha256(),'held_out_values':{f:[] for f in H.MULTIVALUED},
                'held_out_operations':list(H.HELD_OUT_OPERATIONS),
                'held_out_compositions':data['composition_holdouts']['held_out_sets'],
                'arms':{a:{'scanned':False,'exposure_count':None,'artifact':None,'sha256':None}
                        for a in ('A','B','C','D','BC','BD')},
                'note':'Old ledger archived. Value withholding disabled; complete coverage requires separate observation audit.'}
            ledger_path.write_text(encoded(ledger))
    assert H.load_registry().sha256()==candidate.sha256()
    with patch.object(H,'PHASE9_APPROVAL',H.ROOT/'validation_v3/resumption/nonexistent_authorization.json'):
        try: H.load_registry()
        except H.Phase9NotApproved: pass
        else: raise AssertionError('Missing authorization accepted')
    print('PASS: deterministic A-002 registry; preserved entity/operation/composition holdouts; zero literal exclusions; tamper and missing-anchor rejection.')
    print('Registry SHA256:',candidate.sha256())

if __name__=='__main__': main()

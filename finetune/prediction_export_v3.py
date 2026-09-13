"""Export in-memory generation records without grading or granting a release.

The generation caller must authorize input access before obtaining these records.
This module neither reads benchmark files nor creates approval artifacts.
"""
import hashlib
import json
from pathlib import Path

VERSION = 'prediction_export_A002.1'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def export_predictions(root, out, records, *, expected_ids, model_kind,
                       model_revision, adapter_path=None, runtime=None):
    root, out = Path(root).resolve(), Path(out).resolve()
    if not out.is_relative_to(root):
        raise ValueError('Export must be inside repository')
    if out.exists():
        raise FileExistsError('Refusing to overwrite an export')
    records = list(records)
    ids = [r['example_id'] for r in records]
    expected_ids = list(expected_ids)
    if (not ids or len(ids) != len(set(ids)) or
        len(expected_ids) != len(set(expected_ids)) or set(ids) != set(expected_ids)):
        raise ValueError('Require every expected ID exactly once')
    prompt = root / 'datasets_v3/PROMPT_TEMPLATES_A002.json'
    contract = root / 'finetune/structured_prompt_v3.py'
    config = json.loads(prompt.read_text())
    if model_revision != config['model_revision']:
        raise ValueError('Unexpected base revision')
    adapter_hash = None
    adapter_name = None
    if model_kind == 'adapter':
        if adapter_path is None:
            raise ValueError('Adapter file required')
        adapter = (root / adapter_path).resolve()
        if not adapter.is_relative_to(root) or not adapter.is_file():
            raise ValueError('Adapter must be a repository file')
        adapter_hash, adapter_name = sha(adapter), str(adapter.relative_to(root))
    elif model_kind != 'base' or adapter_path is not None:
        raise ValueError('Explicit base/adapter identity required')
    prompts, exported = {}, []
    for record in records:
        # Hash the actual rendered text retained by generation, not a supplied digest.
        text = record.get('rendered_prompt')
        if not isinstance(text, str) or not text:
            raise ValueError('Actual rendered prompt required')
        if not isinstance(record.get('raw_output'), str):
            raise ValueError('Raw output must be explicit, including failures')
        for key in ('question', 'condition', 'seed', 'stopped_at_max_new_tokens'):
            if key not in record:
                raise ValueError('Missing generation field: ' + key)
        if type(record['stopped_at_max_new_tokens']) is not bool:
            raise ValueError('Truncation flag must be boolean')
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        if 'prompt_hash' in record and record['prompt_hash'] != digest:
            raise ValueError('Supplied prompt hash disagrees with rendered text')
        if 'adapter_hash' in record and record['adapter_hash'] != adapter_hash:
            raise ValueError('Supplied adapter hash disagrees with artifact')
        prompts[record['example_id']] = digest
        exported.append({**record, 'prompt_hash': digest, 'adapter_hash': adapter_hash})
    # Validate and serialize completely before creating output files.
    payload = ''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in exported)
    manifest = {'version': VERSION, 'model_kind': model_kind,
                'model_revision': model_revision, 'adapter_path': adapter_name,
                'prompt_artifact_sha256': sha(prompt), 'structured_prompt_sha256': sha(contract),
                'prompt_hashes': prompts, 'expected_count': len(expected_ids),
                'predictions_sha256': hashlib.sha256(payload.encode('utf-8')).hexdigest()}
    runtime_payload = None
    if runtime is not None:
        runtime_payload = json.dumps(runtime, indent=2, allow_nan=False) + '\n'
        manifest['runtime_sha256'] = hashlib.sha256(runtime_payload.encode('utf-8')).hexdigest()
    out.mkdir(parents=True, exist_ok=False)
    pred = out / 'predictions.jsonl'
    pred.write_text(payload, encoding='utf-8')
    identity = out / 'identity.json'
    identity.write_text(json.dumps(manifest, indent=2) + '\n')
    pins = {str(p.relative_to(root)): sha(p) for p in (pred, identity, prompt, contract)}
    if runtime_payload is not None:
        runtime_path = out / 'runtime.json'
        runtime_path.write_text(runtime_payload, encoding='utf-8')
        pins[str(runtime_path.relative_to(root))] = sha(runtime_path)
    if adapter_name:
        pins[adapter_name] = adapter_hash
    registration = {'approved': False, 'sha256': pins,
                    'prediction_identity_manifests': {str(pred.relative_to(root)): str(identity.relative_to(root))},
                    'note': 'Export registration only; not authorization to generate, unseal, or score.'}
    (out / 'registration.json').write_text(json.dumps(registration, indent=2) + '\n')
    return registration

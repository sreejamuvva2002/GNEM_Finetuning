"""Explicitly released, tool-free protected generation. Does not score outputs."""
import argparse
import json
from pathlib import Path
from generation_core_v3 import LocalTransformersBackend, generate_and_export
from prediction_export_v3 import sha

ROOT = Path(__file__).resolve().parent.parent
RELEASE_NAME = 'validation_v3/GENERATION_RELEASE_A002.json'
DEPENDENCIES = ('finetune/final_generate_v3.py', 'finetune/generation_core_v3.py',
                'finetune/prediction_export_v3.py', 'finetune/structured_prompt_v3.py',
                'datasets_v3/PROMPT_TEMPLATES_A002.json')


def pinned(root, release, name):
    if not isinstance(name, str):
        raise RuntimeError('Artifact path required')
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise RuntimeError('Missing or external artifact: ' + name)
    if release.get('sha256', {}).get(str(path.relative_to(root))) != sha(path):
        raise RuntimeError('Unpinned or drifted artifact: ' + name)
    return path


def authorize_generation(root, release, run_id):
    """Hash protected bytes, but never parse their questions before authorization."""
    root = Path(root).resolve()
    if release.get('approved') is not True or release.get('purpose') != 'protected_generation':
        raise RuntimeError('Approved generation release required')
    runs = release.get('runs', [])
    matches = [r for r in runs if r.get('run_id') == run_id]
    if len(matches) != 1:
        raise RuntimeError('Run must be listed exactly once')
    run = matches[0]
    if run.get('mode') != 'memory':
        raise RuntimeError('This entry point is tool-free memory generation only')
    if type(run.get('seed')) not in (int, type(None)):
        raise RuntimeError('Invalid run seed')
    for name in DEPENDENCIES:
        pinned(root, release, name)
    inputs = pinned(root, release, run['inputs'])
    if release.get('classification', {}).get(run['inputs']) != 'sealed_inputs':
        raise RuntimeError('Protected input classification required')
    approval = pinned(root, release, 'validation_v3/Q42_HUMAN_APPROVAL_A002.json')
    benchmark = pinned(root, release, 'datasets_v3/probe_42_v3.jsonl')
    evidence = json.loads(approval.read_text())
    if not isinstance(evidence, dict) or evidence.get('approved') is not True or evidence.get('benchmark_sha256') != sha(benchmark):
        raise RuntimeError('Current Q42 approval evidence required')
    spec = pinned(root, release, run['runtime_spec'])
    adapter = None
    if run.get('model_kind') == 'adapter':
        adapter = pinned(root, release, run['adapter_path'])
        if adapter.name != 'adapter_model.safetensors':
            raise RuntimeError('Selected safetensors adapter required')
        pinned(root, release, str(adapter.with_name('adapter_config.json').relative_to(root)))
    elif run.get('model_kind') != 'base' or run.get('adapter_path') is not None:
        raise RuntimeError('Explicit base/adapter identity required')
    out = (root / run['out']).resolve()
    if not out.is_relative_to(root / 'results_v3/sealed_generation') or out.exists():
        raise RuntimeError('New sealed generation output directory required')
    return run, inputs, adapter, spec, out


def exact_spec_match(actual, expected):
    """Compare JSON specifications without Python's bool/number coercion."""
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return (all(type(k) is str for k in actual) and
                all(type(k) is str for k in expected) and
                actual.keys() == expected.keys() and
                all(exact_spec_match(actual[k], expected[k]) for k in actual))
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            exact_spec_match(a, b) for a, b in zip(actual, expected))
    if type(actual) not in (str, int, float, bool, type(None)):
        return False
    if type(actual) is float:
        import math
        if not math.isfinite(actual) or not math.isfinite(expected):
            return False
    return actual == expected


def verify_runtime(actual, spec):
    # Missing, type-substituted, or non-JSON specifications must not pass.
    if (not isinstance(actual, dict) or not isinstance(spec, dict) or
            not exact_spec_match(actual, spec.get('backend_runtime'))):
        raise RuntimeError('Loaded runtime differs from approved specification')


def execute(root, release, run_id, backend_factory=LocalTransformersBackend):
    root = Path(root).resolve()
    run, inputs, adapter, spec_path, out = authorize_generation(root, release, run_id)
    config = json.loads((root / 'datasets_v3/PROMPT_TEMPLATES_A002.json').read_text())
    spec = json.loads(spec_path.read_text())
    if not exact_spec_match(spec.get('prompt_config'), config):
        raise RuntimeError('Prompt/decoding specification mismatch')
    backend = backend_factory(config, adapter_dir=adapter.parent if adapter else None)
    verify_runtime(backend.runtime, spec)
    # Recheck pins after model load, before parsing protected tasks.
    authorize_generation(root, release, run_id)
    items = [json.loads(line) for line in inputs.read_text().splitlines()]
    registration = generate_and_export(root, out, items, backend, prompt_config=config,
        condition=run['condition'], seed=run['seed'], model_kind=run['model_kind'],
        adapter_path=run.get('adapter_path'))
    # A drifted input/run is not usable even if inference finished.
    for name in release['sha256']:
        pinned(root, release, name)
    (out / 'generation_release.json').write_text(json.dumps(release, indent=2) + '\n')
    return registration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--unseal', action='store_true')
    args = parser.parse_args()
    release_path = ROOT / RELEASE_NAME
    if not args.unseal or not release_path.is_file():
        raise RuntimeError('Protected generation remains locked')
    execute(ROOT, json.loads(release_path.read_text()), args.run_id)

if __name__ == '__main__':
    main()

"""Tool-free generation over already-authorized, in-memory tasks.

No benchmark file loading and no approval creation. The future protected CLI must
validate its release before passing tasks here. Injectable backend permits tests
without loading a model; the production backend uses local model artifacts only.
"""
import hashlib
import json
from structured_prompt_v3 import output_instruction


def generate_records(items, backend, *, prompt_config, condition, seed):
    items = list(items)
    ids = [i['example_id'] for i in items]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('Nonempty unique task IDs required')
    decoding = prompt_config['decoding']
    if decoding.get('do_sample') is not False:
        raise ValueError('This protocol requires deterministic decoding')
    limit = decoding['max_new_tokens']
    if type(limit) is not int or limit <= 0:
        raise ValueError('Invalid generation budget')
    records = []
    for item in items:
        # Only the question and declared shape enter the prompt, never golds.
        messages = [
            {'role': 'system', 'content': prompt_config['closed_book_system']},
            {'role': 'user', 'content': item['question'] + '\n' + output_instruction(item)}]
        text = backend.render(messages)
        input_ids = backend.encode(text)
        if len(input_ids) + limit > prompt_config['max_context']:
            raise ValueError('Prompt exceeds context budget; no silent truncation')
        output_ids = backend.generate(input_ids, limit)
        if len(output_ids) > limit:
            raise ValueError('Backend exceeded declared generation budget')
        ended = bool(output_ids and output_ids[-1] in backend.eos_token_ids)
        records.append({'example_id': item['example_id'], 'question': item['question'],
                        'condition': condition, 'seed': seed, 'messages': messages,
                        'rendered_prompt': text, 'raw_output': backend.decode(output_ids),
                        'input_token_ids': input_ids, 'output_token_ids': output_ids,
                        'input_tokens': len(input_ids), 'output_tokens': len(output_ids),
                        'stopped_at_max_new_tokens': len(output_ids) == limit and not ended})
    return records


def collect_environment_identity(torch, device):
    """Record effective software/device settings enforced by runtime matching."""
    import importlib.metadata
    import os
    import platform
    import subprocess
    packages = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata['Name'].lower().replace('_', '-').replace('.', '-')
        if name in packages:
            raise RuntimeError('Duplicate installed distribution: ' + name)
        packages[name] = dist.version
    driver = subprocess.run(
        ['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
        check=True, capture_output=True, text=True, timeout=15)
    drivers = sorted(set(line.strip() for line in driver.stdout.splitlines() if line.strip()))
    if len(drivers) != 1:
        raise RuntimeError('Cannot establish a single NVIDIA driver version')
    props = torch.cuda.get_device_properties(device)
    return {
        'schema': 'generation_environment_v1',
        'python': platform.python_version(),
        'python_implementation': platform.python_implementation(),
        'platform': platform.platform(),
        'packages': dict(sorted(packages.items())),
        'cuda_runtime': torch.version.cuda,
        'cudnn_version': torch.backends.cudnn.version(),
        'nvidia_driver': drivers[0],
        'device': {'type': device.type, 'index': device.index, 'name': props.name,
                   'capability': [props.major, props.minor],
                   'total_memory': props.total_memory},
        'execution': {
            'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
            'deterministic_warn_only': torch.is_deterministic_algorithms_warn_only_enabled(),
            'cudnn_deterministic': torch.backends.cudnn.deterministic,
            'cudnn_benchmark': torch.backends.cudnn.benchmark,
            'cudnn_allow_tf32': torch.backends.cudnn.allow_tf32,
            'matmul_allow_tf32': torch.backends.cuda.matmul.allow_tf32,
            'float32_matmul_precision': torch.get_float32_matmul_precision(),
            'flash_sdp': torch.backends.cuda.flash_sdp_enabled(),
            'math_sdp': torch.backends.cuda.math_sdp_enabled(),
            'mem_efficient_sdp': torch.backends.cuda.mem_efficient_sdp_enabled(),
            'cudnn_sdp': torch.backends.cuda.cudnn_sdp_enabled(),
            'cublas_workspace_config': os.environ.get('CUBLAS_WORKSPACE_CONFIG')},
    }


class LocalTransformersBackend:
    """Load the declared unchanged base, optionally with one selected LoRA adapter."""
    def __init__(self, config, adapter_dir=None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(config['model_id'],
            revision=config['model_revision'], local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(config['model_id'],
            revision=config['model_revision'], local_files_only=True,
            torch_dtype=torch.bfloat16, device_map={'': 0}, attn_implementation='sdpa')
        if adapter_dir is not None:
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(self.model, str(adapter_dir), is_trainable=False)
        self.model.eval()
        eos = self.model.generation_config.eos_token_id
        self.eos_token_ids = set(eos if isinstance(eos, list) else [eos])
        # Explicit config avoids inheriting sampling/beam settings from an adapter.
        self.generation = GenerationConfig(do_sample=False, num_beams=1,
            eos_token_id=eos, pad_token_id=self.tokenizer.eos_token_id,
            bos_token_id=self.tokenizer.bos_token_id, use_cache=True)
        self.runtime = {'model_id': config['model_id'], 'model_revision': config['model_revision'],
                        'environment': collect_environment_identity(torch, self.model.device),
                        'dtype': 'bfloat16', 'attention': 'sdpa', 'device_map': {'': 0},
                        'adapter_directory': str(adapter_dir) if adapter_dir is not None else None,
                        'generation_config': self.generation.to_dict(),
                        'tokenizer_backend_sha256': hashlib.sha256(
                            self.tokenizer.backend_tokenizer.to_str().encode()).hexdigest(),
                        'chat_template_sha256': hashlib.sha256(
                            json.dumps(self.tokenizer.chat_template, sort_keys=True).encode()).hexdigest()}

    def render(self, messages):
        return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    def encode(self, text):
        return self.tokenizer.encode(text, add_special_tokens=False)

    def generate(self, input_ids, limit):
        t = self.torch.tensor([input_ids], device=self.model.device)
        with self.torch.inference_mode():
            result = self.model.generate(input_ids=t, attention_mask=self.torch.ones_like(t),
                generation_config=self.generation, max_new_tokens=limit)
        return result[0, len(input_ids):].tolist()

    def decode(self, ids):
        return self.tokenizer.decode(ids, skip_special_tokens=True)


def generate_and_export(root, out, items, backend, *, prompt_config, condition, seed,
                        model_kind, adapter_path=None):
    """Caller must authorize inputs and verify backend identity before invoking."""
    from prediction_export_v3 import export_predictions
    items = list(items)
    records = generate_records(items, backend, prompt_config=prompt_config,
                               condition=condition, seed=seed)
    return export_predictions(root, out, records, expected_ids=[i['example_id'] for i in items],
        model_kind=model_kind, model_revision=prompt_config['model_revision'],
        adapter_path=adapter_path, runtime=backend.runtime)

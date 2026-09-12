"""Plain-LoRA training driver.

  python -m finetune.train_lora --variant B_facts

bf16 base + LoRA adapters (no 4-bit quantization), gradient checkpointing,
paged 8-bit optimizer. The default base is Qwen2.5-14B in bf16, which needs a
~40 GB+ GPU (A100/H100-class); it will not fit a small consumer card. For a
smoke/debug pass override to a tiny base, e.g.
``--base-model Qwen/Qwen2.5-0.5B-Instruct``.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch

from finetune import kb, preserve
from finetune.variants import DEFAULT_BASE_MODEL, VARIANTS

DATASETS = kb.ROOT / "finetune" / "datasets"
ADAPTERS = kb.ROOT / "finetune" / "adapters"

# Every attention + MLP projection. Fewer targets trains faster but injects
# facts noticeably worse, which is the thing we are trying to measure.
LORA_TARGETS = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]


def load_dataset_file(path: Path, field: str):
    from datasets import Dataset

    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            obj = json.loads(line)
            rows.append({field: obj[field]})
    return Dataset.from_list(rows)


def train(variant_name: str, base_model: str, max_length: int, out_root: Path,
          batch_size: int, grad_accum: int, epochs: float | None,
          lora_r: int | None, seed: int) -> Path:
    from peft import LoraConfig
    from trl import SFTConfig, SFTTrainer

    variant = VARIANTS[variant_name]
    if variant.dataset is None:
        raise SystemExit(f"{variant_name} is a no-training baseline; nothing to train.")

    dataset_path = DATASETS / variant.dataset
    if not dataset_path.exists():
        raise SystemExit(f"missing dataset {dataset_path} -- run: python -m finetune.build_datasets")

    ds = load_dataset_file(dataset_path, variant.data_field)
    out_dir = out_root / variant_name
    out_dir.mkdir(parents=True, exist_ok=True)

    peft_config = LoraConfig(
        r=lora_r or variant.lora_r,
        lora_alpha=(lora_r or variant.lora_r) * 2,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=LORA_TARGETS,
    )

    cfg_kwargs = dict(
        output_dir=str(out_dir),
        num_train_epochs=epochs if epochs is not None else variant.epochs,
        learning_rate=variant.lr,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        max_length=max_length,
        bf16=True,
        logging_steps=10,
        save_strategy="no",
        report_to=[],
        seed=seed,
    )
    if variant.data_field == "text":
        # Plain LM loss over the whole passage -- this is the CPT variant.
        cfg_kwargs["dataset_text_field"] = "text"
        cfg_kwargs["packing"] = True
    else:
        # Chat data: only score the assistant turn, so the model is not trained
        # to reproduce the system prompt or the question.
        cfg_kwargs["assistant_only_loss"] = True

    args = SFTConfig(**cfg_kwargs)

    # Load the model here rather than handing SFTTrainer a repo id and letting it
    # load internally. TRL's default `loss_type="chunked_nll"` patches the base
    # model's forward and reads `original_forward.__func__`; on a model TRL built
    # from a path under transformers 5.14.1 that forward is a functools.partial,
    # which has no `__func__`, and every SFTTrainer construction dies before the
    # first step. A model loaded here keeps forward as an ordinary bound method,
    # so the patch applies cleanly and the chunked loss path -- the one the
    # existing adapters were trained under -- is preserved. (Switching to
    # `loss_type="nll"` also gets past the crash but silently trains on nothing:
    # entropy pinned at ln(vocab) and token accuracy 0.)
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(base_model, dtype=torch.bfloat16)
    trainer = SFTTrainer(model=model, args=args, train_dataset=ds, peft_config=peft_config)

    started = time.time()
    trainer.train()
    elapsed = time.time() - started

    adapter_dir = out_dir / "adapter"
    trainer.save_model(str(adapter_dir))

    meta = {
        "variant": variant_name,
        "description": variant.description,
        "base_model": base_model,
        "dataset": variant.dataset,
        "n_examples": len(ds),
        "field": variant.data_field,
        "answer_mode": variant.answer_mode,
        "epochs": args.num_train_epochs,
        "lr": variant.lr,
        "lora_r": peft_config.r,
        "max_length": max_length,
        "train_seconds": round(elapsed, 1),
        "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2)
        if torch.cuda.is_available() else None,
        # Which code and which data produced these weights. Retraining writes
        # to the same path, so without this an adapter cannot say whether it is
        # the one a given report was measured on -- which is exactly how the
        # 2026-08-10 `D_sql` retrain invalidated numbers nobody knew were stale.
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_commit": preserve.git("rev-parse", "HEAD"),
        "git_dirty": bool(preserve.git("status", "--porcelain")),
        "base_model_revision": preserve.base_model_revision(base_model)[0],
        "dataset_sha256": preserve.sha256_file(data_path)
        if (data_path := DATASETS / (variant.dataset or "")).is_file() else None,
    }
    (out_dir / "train_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return adapter_dir


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True, choices=sorted(VARIANTS))
    ap.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    ap.add_argument("--max-length", type=int, default=1024)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--epochs", type=float, default=None)
    ap.add_argument("--lora-r", type=int, default=None)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", type=Path, default=ADAPTERS)
    args = ap.parse_args()

    train(
        args.variant, args.base_model, args.max_length, args.out,
        args.batch_size, args.grad_accum, args.epochs, args.lora_r, args.seed,
    )


if __name__ == "__main__":
    main()

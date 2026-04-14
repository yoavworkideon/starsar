"""
Fine-tuning pipeline for DeepSeek-R1:14b on STARDAR domain data.
Uses Unsloth for LoRA — efficient on Mac (MPS) and AGX Orin.

Dataset format (JSONL in finetune/dataset/):
  {"instruction": "...", "input": "...", "output": "..."}

Usage:
  python -m finetune.train --dataset finetune/dataset/ --output finetune/stardar-r1-14b
"""

import argparse
import json
from pathlib import Path


def load_dataset(dataset_dir: str) -> list[dict]:
    records = []
    for path in Path(dataset_dir).glob("*.jsonl"):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    print(f"Loaded {len(records)} training examples")
    return records


def format_prompt(record: dict) -> str:
    instruction = record["instruction"]
    inp         = record.get("input", "")
    return (
        f"### Instruction:\n{instruction}\n\n"
        f"### Input:\n{inp}\n\n" if inp else f"### Instruction:\n{instruction}\n\n"
    ) + "### Response:\n"


def train(dataset_dir: str, output_dir: str, max_steps: int = 500):
    try:
        from unsloth import FastLanguageModel
        import torch
    except ImportError:
        print("Unsloth not installed. Run: pip install unsloth")
        print("For Mac MPS: pip install unsloth[mps]")
        return

    records = load_dataset(dataset_dir)
    if not records:
        print("No training data found in", dataset_dir)
        return

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="deepseek-ai/DeepSeek-R1-Distill-Llama-14B",
        max_seq_length=2048,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing=True,
    )

    from trl import SFTTrainer
    from transformers import TrainingArguments
    from datasets import Dataset

    prompts = [
        format_prompt(r) + r["output"] + tokenizer.eos_token
        for r in records
    ]

    dataset = Dataset.from_dict({"text": prompts})

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        args=TrainingArguments(
            output_dir=output_dir,
            max_steps=max_steps,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=20,
            learning_rate=2e-4,
            fp16=False,
            bf16=True,
            logging_steps=10,
            save_steps=100,
            optim="adamw_8bit",
        ),
    )

    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Model saved to {output_dir}")
    print("To use with Ollama: ollama create stardar-r1-14b -f Modelfile")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",    default="finetune/dataset/")
    parser.add_argument("--output",     default="finetune/stardar-r1-14b")
    parser.add_argument("--max-steps",  type=int, default=500)
    args = parser.parse_args()
    train(args.dataset, args.output, args.max_steps)

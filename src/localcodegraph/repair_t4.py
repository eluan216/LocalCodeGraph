"""Gemma E2B NF4 development pilot; separate from the 31B QAT experiment."""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
from .repair import SYSTEM, extract_patch, sha256_file, validate_record

MODEL = "google/gemma-4-E2B-it"
SETTINGS = {"model": MODEL, "quantization": "bitsandbytes-nf4",
            "compute_dtype": "float16", "double_quant": True,
            "max_input_tokens": 4096, "max_issue_tokens": 1536,
            "max_new_tokens": 1024, "do_sample": False,
            "thinking": False, "seed": 0, "attention": "sdpa",
            "study": "t4-e2b-nf4-dev-v1"}

def fit_prompt(tokenizer, record, arm):
    """Same issue prefix in both arms. Reduce context only to meet input cap."""
    validate_record(record)
    issue_ids = tokenizer.encode(record["problem_statement"], add_special_tokens=False)
    issue = (tokenizer.decode(issue_ids[:SETTINGS["max_issue_tokens"]], skip_special_tokens=True)
             if len(issue_ids) > SETTINGS["max_issue_tokens"] else record["problem_statement"])
    context = record["contexts"][arm]["text"]
    def format_text(chars):
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": "ISSUE:\n" + issue +
                     "\n\nPRE-FIX SOURCE CONTEXT:\n" + context[:chars]}]
        return tokenizer.apply_chat_template(messages, tokenize=False,
            add_generation_prompt=True, enable_thinking=False)
    length = len(context)
    text = format_text(length)
    count = len(tokenizer.encode(text, add_special_tokens=False))
    if count > SETTINGS["max_input_tokens"]:
        lo, hi = 0, length
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if len(tokenizer.encode(format_text(mid), add_special_tokens=False)) <= SETTINGS["max_input_tokens"]:
                lo = mid
            else:
                hi = mid - 1
        length = lo
        text = format_text(length)
        count = len(tokenizer.encode(text, add_special_tokens=False))
    if count > SETTINGS["max_input_tokens"]:
        raise ValueError("system/issue exceeds the fixed prompt cap")
    return text, {"input_tokens": count, "context_characters": length,
                  "issue_truncated": len(issue_ids) > SETTINGS["max_issue_tokens"],
                  "context_truncated": length < len(context)}

def load_records(inputs, manifest_path):
    raw = Path(inputs).read_bytes()
    manifest = json.loads(Path(manifest_path).read_text())
    if hashlib.sha256(raw).hexdigest() != manifest["inputs_sha256"]:
        raise ValueError("input checksum mismatch")
    records = sorted([validate_record(json.loads(line)) for line in raw.decode().splitlines()
                      if line.strip()], key=lambda r: r["instance_id"])
    if len(records) != manifest["tasks"] or len({r["instance_id"] for r in records}) != len(records):
        raise ValueError("task manifest differs or IDs repeat")
    return records, manifest

def save_attempt(output, attempt):
    path = output / "attempts" / (attempt["instance_id"] + "." + attempt["arm"] + ".json")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(attempt, ensure_ascii=False) + "\n")
    temporary.replace(path)

def export_predictions(output, records):
    statuses = Counter()
    for arm in ("bm25", "graph"):
        rows = []
        for record in records:
            path = output / "attempts" / (record["instance_id"] + "." + arm + ".json")
            if path.exists():
                event = json.loads(path.read_text())
                statuses[(arm, event["status"])] += 1
                rows.append({"instance_id": record["instance_id"],
                             "model_name_or_path": MODEL + "-bnb-nf4-t4",
                             "model_patch": event["patch"]})
        (output / f"predictions.{arm}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    return {str(key): value for key, value in statuses.items()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    import re
    if not re.fullmatch(r"[0-9a-f]{40}", args.model_revision):
        raise ValueError("model revision must be an immutable SHA")
    records, inputs_manifest = load_records(args.inputs, args.manifest)
    output = Path(args.output_dir)
    versions = {name: importlib.metadata.version(name) for name in
                ("torch", "transformers", "bitsandbytes", "accelerate")}
    config = {"backend_versions": versions, "settings": SETTINGS, "model_revision": args.model_revision,
              "config_sha256": sha256_file(Path(args.model_dir) / "config.json"),
              "inputs_manifest": inputs_manifest, "tasks": [r["instance_id"] for r in records]}
    if output.exists():
        if not args.resume or json.loads((output / "manifest.json").read_text()) != config:
            raise ValueError("existing output differs; never overwrite or mix experiments")
    else:
        output.mkdir(parents=True)
        (output / "attempts").mkdir()
        (output / "manifest.json").write_text(json.dumps(config, indent=2) + "\n")
    import torch
    from transformers import AutoTokenizer, AutoModelForMultimodalLM, BitsAndBytesConfig
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required for this T4 pilot")
    torch.manual_seed(SETTINGS["seed"])
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir, local_files_only=True)
    quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    model = AutoModelForMultimodalLM.from_pretrained(args.model_dir,
        local_files_only=True, quantization_config=quantization, dtype=torch.float16,
        device_map={"": 0}, attn_implementation="sdpa", low_cpu_mem_usage=True)
    model.eval()
    for index, record in enumerate(records):
        order = ("bm25", "graph") if index % 2 == 0 else ("graph", "bm25")
        for arm in order:
            path = output / "attempts" / (record["instance_id"] + "." + arm + ".json")
            if path.exists():
                continue
            event = {"instance_id": record["instance_id"], "arm": arm, "patch": ""}
            start = time.perf_counter()
            inputs = generated = new_ids = None
            try:
                text, info = fit_prompt(tokenizer, record, arm)
                event.update(info)
                event["prompt_sha256"] = hashlib.sha256(text.encode()).hexdigest()
                inputs = tokenizer(text, add_special_tokens=False, return_tensors="pt").to("cuda:0")
                torch.cuda.reset_peak_memory_stats()
                with torch.inference_mode():
                    generated = model.generate(**inputs, do_sample=False,
                        max_new_tokens=SETTINGS["max_new_tokens"], use_cache=True)
                new_ids = generated[0, inputs["input_ids"].shape[-1]:]
                event["output_tokens"] = len(new_ids)
                event["response"] = tokenizer.decode(new_ids, skip_special_tokens=True)
                event["peak_gpu_allocated_bytes"] = torch.cuda.max_memory_allocated()
                event["peak_gpu_reserved_bytes"] = torch.cuda.max_memory_reserved()
                if len(new_ids) >= SETTINGS["max_new_tokens"]:
                    raise ValueError("output hit the fixed generation limit")
                event["patch"] = extract_patch(event["response"])
                event["status"] = "patch" if event["patch"] else "empty"
            except Exception as error:
                event.update(status="error", error=str(error))
                # Do not auto-retry failed attempts or change the model/context.
            finally:
                del inputs, generated, new_ids
                torch.cuda.empty_cache()
            event["seconds"] = time.perf_counter() - start
            save_attempt(output, event)
            print(record["instance_id"], arm, event["status"], flush=True)
            export_predictions(output, records)
    print(json.dumps(export_predictions(output, records), indent=2))

if __name__ == "__main__":
    main()

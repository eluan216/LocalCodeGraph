"""Prepare paired gold-free inputs without inference or target-code execution."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
from run_swebench_lite import obtain_tasks, obtain_source
from localcodegraph import GraphStore
from localcodegraph.indexer import index_python
from localcodegraph.retrieval import context_for_task

def sanitized_record(task, contexts, archive_sha):
    return {"instance_id": task["instance_id"], "repo": task["repo"],
            "base_commit": task["base_commit"], "problem_statement": task["problem_statement"],
            "source_archive_sha256": archive_sha, "contexts": contexts}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="repair-inputs")
    parser.add_argument("--revision", default="6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2")
    parser.add_argument("--holdout-manifest")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=False)
    (output / "upstream-licenses").mkdir()
    with tempfile.TemporaryDirectory() as temporary:
        if args.holdout_manifest:
            from freeze_repair_holdout import obtain_frozen_tasks
            tasks, dataset = obtain_frozen_tasks(Path(temporary), args.holdout_manifest)
        else:
            tasks, dataset = obtain_tasks(Path(temporary), args.revision)
        with (output / "inputs.jsonl").open("w", encoding="utf-8") as stream:
            for task in tasks:
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    source, archive_sha = obtain_source(task, root)
                    with GraphStore(root / "graph.sqlite") as store:
                        index_python(source, store)
                        contexts = {}
                        for arm in ("bm25", "graph"):
                            value = context_for_task(store, task["problem_statement"],
                                seed_k=10 if arm == "bm25" else 5,
                                hops=0 if arm == "bm25" else 1, max_nodes=30,
                                max_results=10, max_chars=8000, neighbors_per_node=20)
                            contexts[arm] = {"text": value["context"],
                                "selected": [n["id"] for n in value["selected"]],
                                "characters": value["characters"]}
                    stream.write(json.dumps(sanitized_record(task, contexts, archive_sha),
                                            ensure_ascii=False) + "\n")
                    with tarfile.open(root / "source.tar.gz", "r:gz") as tar:
                        for member in tar:
                            parts = Path(member.name).parts
                            if member.isfile() and len(parts) == 2 and member.size < 1_000_000:
                                if parts[-1].lower().startswith(("license", "copying", "notice")):
                                    target = output / "upstream-licenses" / task["instance_id"]
                                    target.mkdir(exist_ok=True)
                                    (target / parts[-1]).write_bytes(tar.extractfile(member).read())
                print("Prepared " + task["instance_id"], flush=True)
    raw = (output / "inputs.jsonl").read_bytes()
    manifest = {"dataset": dataset, "tasks": len(tasks),
                "inputs_sha256": hashlib.sha256(raw).hexdigest(),
                "license": "Quoted source and issues retain upstream terms.",
                "protocol": "benchmarks/REPAIR_PROTOCOL.md"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Prepared gold-free bundle: " + manifest["inputs_sha256"])

if __name__ == "__main__":
    main()

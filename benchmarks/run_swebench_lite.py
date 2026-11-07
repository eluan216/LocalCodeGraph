"""Frozen real-issue retrieval study. Download source; never execute target projects."""
import argparse
from collections import defaultdict
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import random
import re
import resource
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

DATASET = "princeton-nlp/SWE-bench_Lite"

def download(url, path):
    last = None
    for _ in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "LocalCodeGraph-evaluation/1"})
            with urllib.request.urlopen(request, timeout=120) as response, open(path, "wb") as output:
                shutil.copyfileobj(response, output)
            return
        except Exception as error:
            last = error
    raise RuntimeError(f"download failed: {url}: {last}")

def obtain_tasks(root, revision=None):
    import pyarrow.parquet as pq
    metadata = root / "dataset.json"
    download(f"https://huggingface.co/api/datasets/{DATASET}", metadata)
    info = json.loads(metadata.read_text())
    revision = revision or info["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("dataset revision must be a full commit SHA")
    # Resolve filenames at the pinned revision, not a potentially changed main.
    download(f"https://huggingface.co/api/datasets/{DATASET}/revision/{revision}", metadata)
    info = json.loads(metadata.read_text())
    files = sorted(s["rfilename"] for s in info["siblings"]
                   if s["rfilename"].startswith("data/dev-") and s["rfilename"].endswith(".parquet"))
    if not files:
        raise ValueError("dev parquet shards not found")
    rows, manifests = [], []
    for number, name in enumerate(files):
        path = root / f"dev-{number}.parquet"
        download(f"https://huggingface.co/datasets/{DATASET}/resolve/{revision}/{name}", path)
        manifests.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        rows.extend(pq.read_table(path).to_pylist())
    rows.sort(key=lambda task: task["instance_id"])
    if len(rows) != 23 or len({r["instance_id"] for r in rows}) != 23:
        raise ValueError("expected exactly 23 unique development tasks")
    return rows, {"dataset": DATASET, "revision": revision, "split": "dev", "files": manifests}

def obtain_source(task, directory):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", task["repo"]):
        raise ValueError("invalid repository name")
    if not re.fullmatch(r"[0-9a-f]{40}", task["base_commit"]):
        raise ValueError("base_commit must be a full SHA")
    archive = directory / "source.tar.gz"
    download(f'https://codeload.github.com/{task["repo"]}/tar.gz/{task["base_commit"]}', archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    source = directory / "source"
    source.mkdir()
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            # Materialize only bounded regular Python files, never links.
            if not member.isfile() or not member.name.endswith(".py") or member.size > 1_000_000:
                continue
            parts = Path(member.name).parts[1:]
            if not parts or any(p in {"..", ""} for p in parts):
                raise ValueError("unsafe archive path")
            target = source.joinpath(*parts)
            if not target.resolve().is_relative_to(source.resolve()):
                raise ValueError("unsafe archive path")
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as content, target.open("wb") as output:
                shutil.copyfileobj(content, output)
    return source, digest

def reference_labels(patch, store):
    """Invoked after predictions; no gold content is added to the search index."""
    from unidiff import PatchSet
    files, symbols = set(), set()
    for changed in PatchSet(patch):
        old = changed.source_file.removeprefix("a/")
        new = changed.target_file.removeprefix("b/")
        path = new if old == "/dev/null" else old
        files.add(path)
        candidates = [dict(row) for row in store.db.execute(
            "SELECT id,start_line,end_line FROM nodes WHERE path=? AND kind IN ('Function','Method')",
            (path,))]
        touched = set()
        for hunk in changed:
            cursor = max(1, hunk.source_start)
            for line in hunk:
                if line.is_removed:
                    touched.add(line.source_line_no)
                    cursor = line.source_line_no + 1
                elif line.is_added:
                    touched.add(max(1, cursor))
                elif line.is_context:
                    cursor = line.source_line_no + 1
        for number in touched:
            enclosing = [n for n in candidates if n["start_line"] <= number <= n["end_line"]]
            if enclosing:
                smallest = min(enclosing, key=lambda n: (n["end_line"] - n["start_line"], n["id"]))
                symbols.add(smallest["id"])
    if not files:
        raise ValueError("reference patch contains no files")
    return files, symbols

def metrics(predicted, gold):
    # predicted may contain duplicate file paths; dedup preserves first rank.
    predicted = list(dict.fromkeys(predicted))
    hit = set(predicted) & gold
    first = next((i for i, item in enumerate(predicted, 1) if item in gold), None)
    return {"recall": len(hit) / len(gold) if gold else None,
            "hit": int(bool(hit)), "mrr": 1 / first if first else 0}

def worker(task, directory, ordinal):
    from localcodegraph import GraphStore
    from localcodegraph.indexer import index_python
    from localcodegraph.retrieval import context_for_task
    source, archive_sha = obtain_source(task, directory)
    database = directory / "graph.sqlite"
    with GraphStore(database) as store:
        start = time.perf_counter()
        index = index_python(source, store)
        indexing_seconds = time.perf_counter() - start
        if index["nodes"] == 0:
            raise ValueError("empty index")
        arms, times = {}, defaultdict(list)
        for repeat in range(3):
            order = ["bm25", "graph"] if (ordinal + repeat) % 2 == 0 else ["graph", "bm25"]
            for arm in order:
                start = time.perf_counter()
                result = context_for_task(store, task["problem_statement"],
                    seed_k=10 if arm == "bm25" else 5, hops=0 if arm == "bm25" else 1,
                    max_nodes=30, max_results=10, max_chars=8000, neighbors_per_node=20)
                times[arm].append(time.perf_counter() - start)
                ids = [n["id"] for n in result["selected"]]
                if arm in arms and ids != arms[arm]["nodes"]:
                    raise ValueError("nondeterministic retrieval")
                arms[arm] = {"nodes": ids, "files": [store.node(i)["path"] for i in ids],
                             "characters": result["characters"], "visited": result["visited"]}
        # Gold patch is first consulted here, after every retrieval call.
        gold_files, gold_symbols = reference_labels(task["patch"], store)
        indexed_files = {row[0] for row in store.db.execute("SELECT DISTINCT path FROM nodes")}
        for arm, prediction in arms.items():
            prediction["file_metrics"] = metrics(prediction["files"], gold_files)
            prediction["symbol_metrics"] = metrics(prediction["nodes"], gold_symbols)
            prediction["median_retrieval_seconds"] = statistics.median(times[arm])
        return {"id": task["instance_id"], "repo": task["repo"], "base_commit": task["base_commit"],
                "query_sha256": hashlib.sha256(task["problem_statement"].encode()).hexdigest(),
                "archive_sha256": archive_sha, "gold_files": sorted(gold_files),
                "gold_symbols_proxy": sorted(gold_symbols),
                "unindexed_gold_files": sorted(gold_files - indexed_files),
                "index": index, "indexing_seconds": indexing_seconds,
                "database_bytes": database.stat().st_size,
                "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "predictions": arms}

def interval(values, groups=None):
    if not values:
        return None
    rng = random.Random(0)
    samples = []
    if groups is None:
        for _ in range(2000):
            samples.append(statistics.mean(rng.choices(values, k=len(values))))
    else:
        grouped = defaultdict(list)
        for group, value in zip(groups, values):
            grouped[group].append(value)
        keys = sorted(grouped)
        for _ in range(2000):
            selected = rng.choices(keys, k=len(keys))
            samples.append(statistics.mean(v for key in selected for v in grouped[key]))
    samples.sort()
    return [samples[49], samples[1949]]

def summarize(records):
    summary = {"tasks": len(records), "completed": sum("error" not in r for r in records),
               "repositories": len({r["repo"] for r in records}), "arms": {}}
    for arm in ("bm25", "graph"):
        rows = [r["predictions"][arm] for r in records if "error" not in r]
        summary["arms"][arm] = {
            # Failures remain in the primary denominator, contributing zero.
            "mean_file_recall": sum(r["file_metrics"]["recall"] for r in rows) / len(records),
            "file_hit_rate": sum(r["file_metrics"]["hit"] for r in rows) / len(records),
            "file_mrr": sum(r["file_metrics"]["mrr"] for r in rows) / len(records),
            "median_context_characters": statistics.median(r["characters"] for r in rows) if rows else None,
            "median_retrieval_seconds": statistics.median(r["median_retrieval_seconds"] for r in rows) if rows else None,
            "symbol_labeled_tasks": sum(r["symbol_metrics"]["recall"] is not None for r in rows),
            "mean_symbol_proxy_recall": statistics.mean(
                r["symbol_metrics"]["recall"] for r in rows
                if r["symbol_metrics"]["recall"] is not None)
                if any(r["symbol_metrics"]["recall"] is not None for r in rows) else None}
    deltas = [(r["predictions"]["graph"]["file_metrics"]["recall"] -
               r["predictions"]["bm25"]["file_metrics"]["recall"]) if "error" not in r else 0
              for r in records]
    summary.update({"paired_file_recall_delta": statistics.mean(deltas),
                    "paired_task_bootstrap_95_ci": interval(deltas),
                    "repository_cluster_bootstrap_95_ci": interval(deltas, [r["repo"] for r in records]),
                    "wins": sum(v > 0 for v in deltas), "losses": sum(v < 0 for v in deltas),
                    "ties": sum(v == 0 for v in deltas), "complete": all("error" not in r for r in records)})
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/real-world.json")
    parser.add_argument("--revision")
    parser.add_argument("--worker")
    parser.add_argument("--ordinal", type=int, default=0)
    args = parser.parse_args()
    if args.worker:
        task = json.loads(Path(args.worker).read_text())
        with tempfile.TemporaryDirectory() as directory:
            result = worker(task, Path(directory), args.ordinal)
        print(json.dumps(result))
        return
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        tasks, manifest = obtain_tasks(root, args.revision)
        records = []
        for ordinal, task in enumerate(tasks):
            path = root / "task.json"
            path.write_text(json.dumps(task))
            print(f'Evaluating {ordinal + 1}/{len(tasks)} {task["instance_id"]}', flush=True)
            try:
                process = subprocess.run([sys.executable, __file__, "--worker", str(path),
                                          "--ordinal", str(ordinal)],
                                         capture_output=True, text=True, timeout=600, check=True)
                record = json.loads(process.stdout)
            except Exception as error:
                detail = getattr(error, "stderr", None) or str(error)
                record = {"id": task["instance_id"], "repo": task["repo"],
                          "base_commit": task["base_commit"], "error": detail[-4000:]}
            records.append(record)
            output.write_text(json.dumps({"dataset": manifest, "records": records}, indent=2))
    summary = summarize(records)
    # Keep skipped-file details in raw records, not compact log summaries.
    result = {"protocol": "benchmarks/PROTOCOL.md", "dataset": manifest,
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              "cpu": platform.processor(), "cpu_count": os.cpu_count(),
                              "commit": os.environ.get("GITHUB_SHA"),
                              "run_id": os.environ.get("GITHUB_RUN_ID")},
              "summary": summary, "records": records}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("LCG_RESULT_JSON=" + json.dumps(result), flush=True)
    if not summary["complete"]:
        raise SystemExit("Evaluation incomplete; inspect recorded failures.")

if __name__ == "__main__":
    main()

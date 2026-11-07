"""Budget-matched retrieval evaluation and paired bootstrap comparisons."""
import argparse
import hashlib
import json
import platform
import random
import time
from pathlib import Path
from .retrieval import context_for_task
from .store import GraphStore, limit

def evaluate(store, tasks, k=10, mode="lexical", max_chars=16000):
    limit(k, 500)
    limit(max_chars, 1_000_000)
    if mode not in {"lexical", "hybrid"}:
        raise ValueError("mode must be lexical or hybrid")
    records, seen = [], set()
    for task in tasks:
        identifier = task["id"]
        if identifier in seen:
            raise ValueError("duplicate task id")
        seen.add(identifier)
        gold = set(task["relevant_nodes"])
        if not gold:
            raise ValueError("each task requires relevant_nodes")
        missing = [node for node in gold if store.node(node) is None]
        if missing:
            raise ValueError(f"gold nodes missing from snapshot: {missing}")
        start = time.perf_counter()
        # Baseline can use all k lexical seeds. Graph reserves half for expansion.
        seed_k = k if mode == "lexical" else (max(1, k // 2) if k else 0)
        result = context_for_task(store, task["query"], seed_k=seed_k,
                                  max_nodes=min(500, max(30, k * 3)), max_results=k,
                                  max_chars=max_chars, hops=0 if mode == "lexical" else 1)
        predicted = [hit["id"] for hit in result["selected"]]
        elapsed = time.perf_counter() - start
        hits = set(predicted) & gold
        first = next((rank for rank, node in enumerate(predicted, 1) if node in gold), None)
        records.append({"id": identifier, "recall_at_k": len(hits) / len(gold),
                        "reciprocal_rank": 1 / first if first else 0,
                        "hit_at_k": int(bool(hits)), "seconds": elapsed,
                        "characters": result["characters"], "visited": result["visited"],
                        "predicted": predicted})
    count = len(records)
    return {"mode": mode, "k": k, "max_chars": max_chars, "tasks": count,
            "mean_recall_at_k": sum(r["recall_at_k"] for r in records) / count if count else None,
            "mrr": sum(r["reciprocal_rank"] for r in records) / count if count else None,
            "records": records}

def compare(store, tasks, k=10, max_chars=16000, bootstrap_samples=2000, seed=0):
    """Intervals resample paired tasks, not repositories; no patch-quality inference."""
    if not 100 <= bootstrap_samples <= 10000:
        raise ValueError("bootstrap_samples must be between 100 and 10000")
    tasks = list(tasks)
    baseline = evaluate(store, tasks, k, "lexical", max_chars)
    candidate = evaluate(store, tasks, k, "hybrid", max_chars)
    deltas, wins, losses, ties = [], [], [], []
    for before, after in zip(baseline["records"], candidate["records"]):
        delta = after["recall_at_k"] - before["recall_at_k"]
        deltas.append(delta)
        (wins if delta > 0 else losses if delta < 0 else ties).append(before["id"])
    interval = None
    if deltas:
        rng = random.Random(seed)
        samples = sorted(sum(rng.choices(deltas, k=len(deltas))) / len(deltas)
                         for _ in range(bootstrap_samples))
        interval = [samples[int(0.025 * (bootstrap_samples - 1))],
                    samples[int(0.975 * (bootstrap_samples - 1))]]
    return {"baseline": baseline, "candidate": candidate,
            "paired_mean_recall_delta": sum(deltas) / len(deltas) if deltas else None,
            "paired_task_bootstrap_95_ci": interval,
            "bootstrap_seed": seed, "bootstrap_samples": bootstrap_samples,
            "wins": wins, "losses": losses, "ties": ties,
            "scope": "Only these tasks, this snapshot and these retrieval budgets. "
                     "Task bootstrap does not account for within-repository correlation. "
                     "This is not evidence of improved Kaggle patch success."}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--mode", choices=["lexical", "hybrid", "compare"], default="lexical")
    parser.add_argument("-k", type=int, default=10)
    parser.add_argument("--max-chars", type=int, default=16000)
    parser.add_argument("--output")
    args = parser.parse_args()
    raw = Path(args.tasks).read_bytes()
    tasks = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    with GraphStore(args.db) as store:
        result = (compare(store, tasks, args.k, args.max_chars) if args.mode == "compare"
                  else evaluate(store, tasks, args.k, args.mode, args.max_chars))
        result["snapshot_metadata"] = {row["key"]: json.loads(row["value"])
                                      for row in store.db.execute("SELECT * FROM metadata")}
    result["environment"] = {"python": platform.python_version(), "platform": platform.platform(),
                             "tasks_sha256": hashlib.sha256(raw).hexdigest()}
    output = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)

if __name__ == "__main__":
    main()

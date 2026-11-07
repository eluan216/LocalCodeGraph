"""Retrieval-only evaluation; does not estimate patch success."""
import argparse
import json
import time
from pathlib import Path
from .retrieval import context_for_task
from .store import GraphStore, limit

def evaluate(store, tasks, k=10, mode="lexical"):
    limit(k, 500)
    if mode not in {"lexical", "hybrid"}:
        raise ValueError("mode must be lexical or hybrid")
    records = []
    seen = set()
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
        if mode == "lexical":
            predicted = [hit["id"] for hit in store.search(task["query"], k)]
        else:
            result = context_for_task(store, task["query"], seed_k=max(1, k // 2), max_nodes=k,
                                      max_chars=1_000_000, hops=1)
            predicted = [hit["id"] for hit in result["selected"]]
        elapsed = time.perf_counter() - start
        hits = set(predicted) & gold
        first = next((rank for rank, node in enumerate(predicted, 1) if node in gold), None)
        records.append({"id": identifier, "recall_at_k": len(hits) / len(gold),
                        "reciprocal_rank": 1 / first if first else 0,
                        "seconds": elapsed, "predicted": predicted})
    count = len(records)
    return {"mode": mode, "k": k, "tasks": count,
            "mean_recall_at_k": sum(r["recall_at_k"] for r in records) / count if count else None,
            "mrr": sum(r["reciprocal_rank"] for r in records) / count if count else None,
            "records": records}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--mode", choices=["lexical", "hybrid"], default="lexical")
    parser.add_argument("-k", type=int, default=10)
    args = parser.parse_args()
    tasks = [json.loads(line) for line in Path(args.tasks).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    with GraphStore(args.db) as store:
        print(json.dumps(evaluate(store, tasks, args.k, args.mode), indent=2))

if __name__ == "__main__":
    main()

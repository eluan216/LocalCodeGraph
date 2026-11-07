"""Ranked graph expansion with explicit context, traversal and freshness limits."""
import heapq
from .store import limit

def reciprocal_rank_fusion(*rankings, constant=60):
    if constant <= 0:
        raise ValueError("constant must be positive")
    scores = {}
    for ranking in rankings:
        seen = set()
        for rank, hit in enumerate(ranking, 1):
            identifier = hit["id"]
            if identifier in seen:
                continue
            seen.add(identifier)
            scores[identifier] = scores.get(identifier, 0.0) + 1 / (constant + rank)
    return [{"id": key, "score": score} for key, score in
            sorted(scores.items(), key=lambda item: (-item[1], item[0]))]

def context_for_task(store, query, *, dense_hits=(), seed_k=10, max_nodes=30,
                     max_chars=16000, hops=1, neighbors_per_node=20,
                     max_results=None, root=None):
    """Pack whole snippets. root enables fail-closed stale-source rejection.

    Graph scores decay with distance. Call/reference edges outrank containment.
    Character limits include source headers and separators, not tokenizer counts.
    """
    for value, ceiling in [(seed_k, 1000), (max_nodes, 500), (max_chars, 1_000_000),
                           (hops, 3), (neighbors_per_node, 1000)]:
        limit(value, ceiling)
    max_results = max_nodes if max_results is None else limit(max_results, 500)
    dense_hits = list(dense_hits)
    seeds = reciprocal_rank_fusion(store.search(query, seed_k), dense_hits)
    frontier, best, visited = [], {}, set()
    chunks, selected, emitted, skipped = [], [], [], []
    chars = 0

    def enqueue(identifier, score, depth, via):
        node = store.node(identifier)
        if node is None:
            return
        # Module snippets duplicate symbol bodies and often consume the budget.
        adjusted = score * (0.35 if node["kind"] in {"File", "Module"} else 1)
        previous = best.get(identifier, -1)
        if adjusted > previous and identifier not in visited:
            best[identifier] = adjusted
            heapq.heappush(frontier, (-adjusted, identifier, depth, via))

    for hit in seeds[:seed_k]:
        enqueue(hit["id"], hit["score"], 0, "retrieval")
    while frontier and len(visited) < max_nodes and len(selected) < max_results:
        negative_score, identifier, depth, via = heapq.heappop(frontier)
        if identifier in visited or -negative_score < best[identifier]:
            continue
        visited.add(identifier)
        node = store.node(identifier)
        if root is not None and not store.is_fresh(identifier, root):
            skipped.append({"id": identifier, "reason": "stale_or_unverifiable"})
            continue
        duplicate = any(
            node["path"] == old["path"]
            and (node["start_line"] <= old["start_line"] <= old["end_line"] <= node["end_line"]
                 or old["start_line"] <= node["start_line"] <= node["end_line"] <= old["end_line"])
            and (node["text"] in old["text"] or old["text"] in node["text"])
            for old in emitted)
        header = f'{identifier} | {node["path"]}:{node["start_line"]}-{node["end_line"]}\n'
        chunk = header + node["text"]
        separator = "\n\n" if chunks else ""
        if duplicate:
            skipped.append({"id": identifier, "reason": "overlapping_source"})
        elif chars + len(separator) + len(chunk) <= max_chars:
            chunks.append(chunk)
            chars += len(separator) + len(chunk)
            emitted.append(node)
            selected.append({"id": identifier, "depth": depth, "via": via,
                             "score": -negative_score})
        else:
            skipped.append({"id": identifier, "reason": "context_budget"})
        if depth < hops:
            for edge in store.get_code_neighbors(identifier, max_neighbors=neighbors_per_node):
                other = edge["target"] if edge["source"] == identifier else edge["source"]
                weight = {"calls": 0.8, "references": 0.75, "inherits": 0.65,
                          "imports": 0.5, "contains": 0.15}.get(edge["type"], 0.4)
                enqueue(other, -negative_score * weight, depth + 1, edge["type"])
    return {"context": "\n\n".join(chunks), "selected": selected,
            "visited": len(visited), "characters": chars, "skipped": skipped,
            "budget_unit": "characters", "freshness_checked": root is not None,
            "fallback": "lexical_only" if not dense_hits else "none"}

"""Deterministic rank fusion and bounded, evidence-bearing graph expansion."""
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
                     max_chars=16000, hops=1, neighbors_per_node=20):
    """Character budget includes headers and separators; does not claim tokenizer parity."""
    limit(seed_k)
    limit(max_nodes, 500)
    limit(max_chars, 1_000_000)
    limit(hops, 3)
    limit(neighbors_per_node)
    seeds = reciprocal_rank_fusion(store.search(query, seed_k), dense_hits)
    queue = [(hit["id"], 0, "retrieval") for hit in seeds[:seed_k]]
    visited, chunks, selected = set(), [], []
    chars = 0
    position = 0
    # max_nodes bounds traversal even when a node is too large to emit.
    while position < len(queue) and len(visited) < max_nodes:
        identifier, depth, via = queue[position]
        position += 1
        if identifier in visited:
            continue
        visited.add(identifier)
        node = store.node(identifier)
        if node is None:
            continue
        header = f'{identifier} | {node["path"]}:{node["start_line"]}-{node["end_line"]}\n'
        chunk = header + node["text"]
        separator = "\n\n" if chunks else ""
        if chars + len(separator) + len(chunk) <= max_chars:
            chunks.append(chunk)
            chars += len(separator) + len(chunk)
            selected.append({"id": identifier, "depth": depth, "via": via})
        if depth < hops:
            for edge in store.get_code_neighbors(identifier, max_neighbors=neighbors_per_node):
                other = edge["target"] if edge["source"] == identifier else edge["source"]
                queue.append((other, depth + 1, edge["type"]))
    return {"context": "\n\n".join(chunks), "selected": selected,
            "visited": len(visited), "characters": chars,
            "budget_unit": "characters",
            "fallback": "lexical_only" if not dense_hits else "none"}

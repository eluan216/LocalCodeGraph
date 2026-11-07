# LocalCodeGraph

Offline, bounded repository context for local coding agents.

**Research prototype:** no benchmark gain, Kaggle score, full harness compatibility, or model memory-fit claim has been established.

## Quick start

Python 3.10+ with SQLite FTS5. The core has no third-party runtime dependencies.

```bash
python -m pip install -e .
lcg --db demo.sqlite index examples/toy_repo
lcg --db demo.sqlite search "decode input"
lcg --db demo.sqlite context "decode input" --max-chars 8000
python -m unittest discover -s tests -v
python -m localcodegraph.evaluation --db demo.sqlite --tasks examples/tasks.jsonl
```

## Implemented

- Atomic SQLite snapshot import, indexed graph edges, induced subgraphs and BM25 lexical search.
- Python AST symbol extraction, containment and approximate same-file lexical call links.
- File hashes and explicit source-freshness checking.
- Reciprocal-rank fusion, bounded graph expansion and context with source locations.
- Optional chunked cosine search over CPU memory-mapped NumPy vectors.
- CLI, retrieval evaluation, synthetic smoke fixture and automated tests.

The default context command combines lexical retrieval with graph expansion. Dense retrieval requires externally supplied compatible embeddings and an encoder; it is not silently substituted with lexical search.

```python
from localcodegraph import GraphStore
from localcodegraph.retrieval import context_for_task

with GraphStore("demo.sqlite") as graph:
    result = context_for_task(graph, "decode input", max_chars=8000)
    print(result["context"])
```

For dense search, install `pip install -e ".[dense]"`, create a floating `vectors.npy` matrix and a JSON list of node IDs in matching row order, and use `DenseIndex.search_vector`. Supply its ranked hits to `context_for_task(..., dense_hits=hits)`. Encoder identity, revision and preprocessing must match the vectors.

## Scope and limitations

The built-in parser currently supports Python, not a multi-language tree-sitter pipeline. Its call links are approximate: assignments, imports, dynamic dispatch, decorators and default-expression calls are not resolved. Inspect source before relying on an edge. Normalized JSON import supports externally generated graphs but is not yet an adapter for the competition's raw assets.

Budgets are measured in characters, not model tokens. Snapshot freshness is an explicit `is_fresh` API; retrieval does not automatically reindex changed files. Dense search bounds temporary vector allocation by chunk size, but this is not a measured peak-memory guarantee.

The toy fixture tests mechanics only. Its metrics are not research results.

## Research and competition

- [Research review and differentiation](docs/research.md)
- [Evaluation protocol](docs/evaluation.md)
- [Snapshot format](docs/schema.md)
- [Competition integration status](competition/README.md)
- [Implementation roadmap](docs/roadmap.md)

This project builds on code graph retrieval research including CodexGraph, RepoGraph and LocAgent. It is an independent implementation; no competitor code or datasets are bundled.

License: Apache-2.0 for original project code. External repositories, model weights and datasets retain their own licenses.

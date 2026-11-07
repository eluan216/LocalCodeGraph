# Roadmap

## Implemented foundation
- SQLite snapshot storage, BM25 and graph queries.
- Python AST parser with documented approximate resolution.
- Chunked dense search, rank fusion and bounded context.
- CLI, retrieval metric runner and synthetic tests.
- Research comparison and experiment protocol.

## Next: official assets and integration
- Inspect actual graph/embedding files and harness wheel from the competition data.
- Pin versions and implement adapters using observed schemas.
- Verify raw response formats and tool restrictions in the official validator.
- Exercise graph-missing and stale-graph fallback paths.
- Produce a validated submission.zip; do not label a hand-written schema as compatible.

## Next: resource evaluation
- Collect a small, licensed corpus with pinned commits and provenance manifests.
- Build audited localization pairs without exposing gold patches to retrieval.
- Run matched retrieval ablations and then faithful patch evaluation.
- Record resource usage, paired uncertainty and all raw results.

## Later, if evidence justifies it
- Multi-language tree-sitter extraction and cross-file resolution.
- Incremental invalidation and automatic stale-snippet rejection.
- Actual tokenizer-based context packing and relevance-aware expansion.
- Expanded dataset and reproduction notebook.
- Paper: write results only after experiments, with negative outcomes retained.

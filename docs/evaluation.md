# Evaluation protocol

## Questions

Does bounded graph expansion improve localization and patch success at equal context and wall-clock budgets? Does it remain useful with stale, incomplete or absent graphs?

## Conditions

1. Filesystem tools only.
2. Lexical BM25.
3. Dense embeddings only.
4. Lexical plus graph.
5. Lexical/dense rank fusion plus graph.
6. Closest feasible LocAgent/RepoGraph reproduction.

Keep model checkpoint, serving backend, sampling, context ceiling, hardware and task limits fixed. Record intentional differences. Compare retrieval-only conditions first; run full repair only after the harness passes gold-patch and no-patch controls.

## Splits and leakage

Pin every repository to the task's base commit, before the fix. Keep gold patches, test patches, post-fix sources and localization labels out of retrieval and agent inputs. Derive labels offline. Changed functions are an imperfect proxy for necessary context; audit sampled cases and mark ambiguity.

Use repository-disjoint development/test splits where feasible, plus chronological splits within repositories. Deduplicate issues and near-duplicate patches across splits. Freeze the final holdout before prompt selection. Public leaderboard feedback is development feedback, not an independent test.

## Measurements

- File/function Recall@1/5/10 and MRR, with explicit denominator and label coverage.
- Patch test pass rate, empty patches, invalid tool calls, repeats and timeouts.
- End-to-end latency including indexing and sandbox setup; report cold and warm runs separately.
- Prompt/output tokens from the actual tokenizer, tool calls, graph coverage, stale-source rates.
- CPU RSS, GPU peak allocation/reservation, vector/index size and model configuration.

Report per-task paired outcomes and uncertainty, not just aggregate improvement. Use multiple seeds for stochastic repair and repository-clustered intervals where feasible. Do not infer patch success from localization metrics.

## Existing command

```bash
python -m localcodegraph.evaluation --db demo.sqlite --tasks examples/tasks.jsonl --mode lexical -k 10
python -m localcodegraph.evaluation --db demo.sqlite --tasks examples/tasks.jsonl --mode hybrid -k 10
```

The hybrid mode means lexical seeds plus graph expansion (no dense encoder). It uses half of k, rounded down with minimum one, as seeds to reserve capacity for neighbors. The lexical baseline can use all k seeds. Both use the same rank-based context packer, source-overlap suppression, max_chars budget and k result cap. Expansion is best-first with distance decay and fixed edge-type weights; these weights are heuristics, not trained parameters. k=0 returns no results.

Use --mode compare --max-chars 8000 --output comparison.json to run both conditions. The report retains every per-task prediction, win, loss and tie. The paired bootstrap uses 2,000 task resamples with seed zero; its 95% percentile interval is descriptive for the supplied tasks and does not correct for within-repository correlation. One-task fixtures produce degenerate intervals and cannot support generalization.

Latency in compare mode runs the baseline first and graph second in the same process, so cache warming can favor the second arm. Treat these timings as diagnostic until a randomized repeated-run timing study is added. The report records task-file SHA256, Python/platform information and stored snapshot metadata. Index creation time is excluded and must be recorded separately.

The identifier tokenizer changed: reindex existing databases to populate the new search terms. Historical lexical results are not directly comparable after reindexing.

JSONL tasks contain id, query, relevant_nodes. Current evaluation targets one snapshot and validates that every gold node exists. Run separately for each task base commit. The included one-task synthetic fixture is only a smoke test.

## Before any paper claim

Save raw traces, configs, commit hashes, environment manifest and per-task outputs. Include failed runs and excluded-task reasons. The full model benchmark, statistical analysis and hardware measurements remain to be implemented and run.

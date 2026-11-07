# SWE-bench Lite development retrieval evaluation v1

Frozen before the first run on 2026-11-07. No parameters will be tuned using these scores.

- Population: every task in the public SWE-bench Lite dev split (expected 23). No score-based selection.
- Dataset: princeton-nlp/SWE-bench_Lite; resolve its immutable revision before loading any tasks and record revision plus parquet SHA256. Subsequent runs may specify --revision.
- Repository: exact base_commit per task. Download Python source from that commit; never import or execute repository code.
- Inputs: problem_statement only, unchanged. No hints, gold patch, test patch or post-fix code enters the graph or query.
- Labels: derive changed source paths from the reference patch AFTER both retrieval predictions are generated. Include all changed source paths, including absent/non-Python paths, in primary file metrics.
- Exploratory symbol proxy: innermost pre-fix function/method intersecting removed lines or insertion anchors. Report label coverage and do not equate these labels with necessary context.
- Baseline: current identifier-aware BM25 with the common source-deduplicating context packer, hops=0, seed_k=10.
- Candidate: same BM25 and packer, seed_k=5, one-hop dependency expansion with existing fixed edge weights.
- Both: at most 10 emitted nodes, 30 visited nodes, 8,000 characters, 20 neighbors per expansion. No dense encoder.
- Run each arm three times, alternate arm order across tasks/repeats. Accuracy uses the first deterministic prediction; latency is diagnostic warm-process median.
- Primary: mean per-task changed-file recall. Secondary: file hit rate, file MRR, exploratory symbol recall, context characters and retrieval seconds.
- Paired task and repository-cluster bootstrap intervals: 2,000 resamples, seed=0. Report wins/losses/ties, all failures and per-repository results.
- Resource observations: per-task indexing wall time, SQLite size, node/edge counts and Linux process high-water RSS including indexing and retrieval. RSS is not arm-specific and does not measure GPU memory.
- No model, no repair generation, no validation-test execution, no Kaggle score inference.
- Failures count as zero primary recall/hit/MRR and make the run incomplete; preserve error messages. Do not silently drop tasks.
- This is a public development study, not a blind held-out benchmark. If its results inform changes, evaluate those changes on a separately frozen test set.

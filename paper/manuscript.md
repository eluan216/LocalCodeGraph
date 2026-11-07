# LocalCodeGraph: A Lightweight, Offline Code-Graph Retrieval Toolkit

**Subtitle:** Budgeted repository context and reproducible evaluation for local software engineering agents

**Author:** eluan216 — replace with preferred publication name before submission  
**Affiliation and correspondence:** To be supplied by the author  
**Draft date:** November 7, 2026  
**Intended venue:** Google – The Gemma 4 Developer Agent Paper Track  
**Status:** Working resource-paper draft with a completed public-development retrieval study; full test-based repair evaluation and competition integration remain incomplete.

## Abstract

Repository navigation is a practical challenge for local software engineering agents. I present LocalCodeGraph, an offline Python toolkit for combining lexical retrieval, optional dense-vector retrieval and bounded code-graph expansion. The current implementation stores normalized snapshots in SQLite, extracts Python symbols with source locations, and searches identifiers using BM25 with naming-boundary normalization. Context selection combines rank fusion, dependency-weighted expansion, overlapping-source suppression and explicit traversal and output limits. Optional file-hash checks reject stale snippets. A comparison runner evaluates lexical and graph retrieval under matched context limits and retains per-task improvements and regressions.

The release includes code, a command-line interface, tests and a reproducible evaluation protocol. On all 23 public SWE-bench Lite development tasks from six repositories, graph retrieval and the configured BM25 baseline both achieve 47.8% changed-file recall at matched output caps. Exploratory symbol-proxy recall rises from 22.7% to 27.3% on 22 labeled tasks, while median context size and retrieval latency increase. The primary result is a tie; the symbol gain depends on one task. A separate user-run Gemma E2B NF4 pilot completed 46 generations on a Colab T4. Only one exported patch both applied and changed source under an additional audit, so parser acceptance is not treated as repair success. Neither study establishes 31B memory fit or improved repair success. Competition integration and a licensed extended dataset remain planned.

## 1. Introduction

A repository-level coding task requires more than finding a text match. Relevant context can span a function, its dependencies and its callers. A lexical search may identify an entry point while missing a dependency whose name differs from the issue description. Graph expansion can recover that context, but can also add irrelevant neighbors and exhaust an agent's budget.

LocalCodeGraph investigates this tradeoff as a retrieval resource. My objective is to make repository context available without a running graph database service, with explicit limits on the amount of work performed and source returned. I do not assume that graph retrieval is universally better than lexical search.

The current contributions are:

1. An offline SQLite toolkit for normalized graph snapshots, lexical search and optional dense retrieval.
2. A context-selection policy with dependency weights, source-overlap suppression, bounded traversal and optional freshness checks.
3. A budget-matched comparison runner that preserves predictions, improvements, regressions and experimental provenance.
4. An open implementation with tests, examples and a documented protocol for future real-world evaluation.

The project targets the resource track. It is not yet a complete competition agent or an extended-dataset release.

## 2. Related Work

**Graph-based repository navigation.** CodexGraph exposes repository structure through graph database queries and evaluates the approach on repository-level tasks [1]. LocalCodeGraph shares the use of explicit structure, but currently provides fixed Python methods and SQLite storage rather than a general graph-query agent.

**Repository context and localization.** RepoGraph integrates repository graphs into software engineering workflows [2]. LocAgent uses graph-guided localization and provides a closely related lightweight representation [3]. These systems make graph-assisted navigation an established approach. LocalCodeGraph's storage format and fixed interfaces alone do not establish methodological novelty.

The intended distinction is a small, inspectable retrieval and evaluation resource focused on bounded context, provenance and offline operation. Direct empirical comparisons with these systems remain necessary before any superiority claim.

## 3. Implementation

### 3.1 Snapshot storage and construction

A snapshot contains nodes, directed typed edges and metadata. Nodes carry an identifier, kind, repository-relative path, inclusive source span, text and an optional file hash. Edge endpoints must refer to existing nodes. SQLite stores both nodes and indexed incoming/outgoing edges. Snapshot replacement is transactional: failed validation or insertion preserves the previous snapshot.

The built-in extractor uses Python's AST. It produces module, class, function and method nodes, containment edges and approximate same-file lexical call links. It does not resolve cross-file imports, assignments or dynamic dispatch. Decorator and default-expression calls are outside the current call analysis. Identifiers include source line numbers and are snapshot-specific.

A normalized JSON importer supports externally constructed snapshots. Direct ingestion of the competition's raw graph and embedding assets has not yet been implemented or validated.

### 3.2 Lexical and dense retrieval

SQLite FTS5 supplies BM25 search. Index and query normalization splits snake_case, camelCase and acronym boundaries. Source snippets themselves remain unchanged.

Optional dense retrieval performs chunked cosine search over a CPU memory-mapped NumPy matrix. The caller supplies matching node IDs and query vectors. The toolkit does not bundle an encoder; vector and query preprocessing must agree. Chunking limits temporary vector allocation but does not establish a measured total-memory bound.

### 3.3 Bounded context selection

Reciprocal-rank fusion combines available lexical and dense rankings. A best-first frontier expands selected seeds. Fixed heuristic weights prioritize call and reference edges over containment edges; scores decay along traversal paths. Whole-module and file candidates are downweighted.

The packer returns complete snippets with source locations. It suppresses nested source snippets when their text repeats source already emitted. Independent controls bound selected results, visited nodes, hop count, neighbors inspected and output characters. Headers and separators count toward the character budget.

When a repository root is supplied, file-hash verification rejects stale or unverifiable snippets before emission or expansion. This does not automatically rebuild the index.

### 3.4 Interfaces and competition boundary

The library provides graph-neighbor queries, induced subgraphs, lexical search and a context_for_task helper. DenseIndex exposes vector search and a query-plus-encoder helper. These are standalone library APIs, not verified replacements for the harness's registered graph tools.

ADK skill packages, exact response-format adapters and a validated submission archive remain future work. No sandbox-compatibility guarantee is made.

## 4. Evaluation and Current Evidence

### 4.1 Functional validation

GitHub Actions verifies installation, indexing, context generation, evaluation and paired-comparison execution on Python 3.10 and 3.12. All 17 tests passed for the implementation evaluated in [4]. Tests cover transaction rollback, induced subgraphs, identifier boundaries, context limits, duplicate-source suppression, freshness rejection and dense-search ordering. Analytical cases exercise both a graph-assisted improvement and a graph-induced regression.

These tests check implementation behavior. Additional evaluation checks validate file-rank deduplication, empty symbol-label handling, pre-fix rename labels, failure denominators and clustered intervals. Accuracy on natural issue descriptions is measured separately below.

### 4.2 Synthetic smoke observation

| Observation | Result | Interpretation |
| --- | --- | --- |
| Tests on each supported CI Python version | 17 passed | Functional validation |
| Toy context, preceding implementation | 540 characters | Included repeated module source |
| Toy context, revised implementation | 291 characters | Repeated source suppressed |
| Toy paired localization comparison | Tie | No measured localization improvement |

The context-size observation concerns one fixture and compares two implementation versions. It is not a comparison against a filesystem agent and does not measure tokens, tool calls, CPU/GPU memory or patch success.

### 4.3 Real-issue retrieval study

I evaluated every task in SWE-bench Lite's public development split: 23 issues across six repositories. Each graph was built from the task's exact pre-fix commit. Issue descriptions were unchanged, and reference patches were first consulted after retrieval for scoring. Dataset revision, archive checksums, code revision and predictions are recorded in [5].

The lexical arm used ten BM25 seeds without expansion. The graph arm used five seeds and the existing one-hop weighted expansion. Both used the same packer, an 8,000-character output cap, a ten-node result cap and a 30-visited-node ceiling. No dense embeddings or language model were used. The protocol was committed before scores were observed, and no retrieval parameters were subsequently tuned.

| Metric | BM25 + common packer | Graph + common packer |
| --- | ---: | ---: |
| Changed-file recall / file hit rate | 47.83% (11/23) | 47.83% (11/23) |
| File MRR | 0.4130 | 0.4130 |
| Exploratory symbol-proxy recall, 22 labeled tasks | 22.73% | 27.27% |
| Median context characters | 6,008 | 7,902 |
| Median diagnostic retrieval latency | 12.36 ms | 12.88 ms |

All tasks completed and all changed source files were indexed. Each task had one changed source path, so file recall and hit rate coincide. Graph retrieval gained one file hit and lost one; 21 tasks tied. The primary paired difference was zero. A seeded 2,000-resample repository-cluster bootstrap interval ranged from -12.5 to +12.5 percentage points, establishing neither equivalence nor superiority.

The graph arm gained a changed-file hit for pvlib-1072 by retrieving helpers, without retrieving the labeled function. It lost astroid-1333 after spending most of its budget on an irrelevant documentation configuration file. For pyvista-4315, it retrieved the changed initializer in an already localized file; this single case explains the exploratory symbol gain.

Symbol labels are the smallest pre-fix functions or methods intersecting removed lines or insertion anchors. They are unaudited proxies, omit one task and need not represent all necessary context. The primary labels are reference-patch source paths.

Three deterministic runs per arm used alternating order; latency is the median within each task, then across tasks. Median indexing time was 0.711 seconds and median SQLite size 11.08 MiB on the CPU runner, excluding downloads and extraction. The constant worker ru_maxrss readings are not interpreted as isolated toolkit-memory measurements.

### 4.4 Interpretation and next evaluation

The run demonstrates feasibility on real issue descriptions but no primary localization improvement. Median returned context was larger for graph retrieval. The lexical arm only inspected ten seeds; an oversampling baseline is needed to distinguish graph structure from candidate-pool effects.

This is a small public development set, not a blind holdout. Same-file approximate edges, whole-snippet packing and truncation to the first 64 normalized unique query terms further constrain interpretation. This retrieval-only study did not involve a model; a separate T4 generation pilot follows. The next study must use an independent frozen split, stronger lexical and prior-work baselines, audited labels, actual token counts and end-to-end patch verification.


### 4.5 Observed E2B generation on a Colab T4

The user supplied all 46 attempt records and both complete prediction exports from an E2B NF4 run on a Tesla T4 with 15,360 MiB. Both arms used the same pinned model revision, greedy decoding, FP16 compute, eager attention, a 4,096-token input limit and a 1,024-token output limit. This is not the official W4A16 QAT checkpoint or a 31B experiment.

| Outcome | BM25 context | Graph context |
| --- | ---: | ---: |
| Completed attempts | 23 | 23 |
| Generator parser accepted | 4 | 10 |
| Ordinary git application passes | 1 | 2 |
| Applies and changes source | 0 | 1 |

Most errors involved malformed hunk counts, unexpected headers or stray fences; two BM25 attempts reached the output cap. Some parser-accepted exports were unchanged edits or failed to match the pre-fix source. The original parser was therefore too permissive to support repair-success reporting.

The largest saved PyTorch reserved-memory readings were 7.64 GiB for BM25 and 7.77 GiB for graph; these exclude non-allocator device memory and do not measure a reduction against a filesystem agent. Median recorded generation times were 21.78 and 20.59 seconds, respectively, with different output lengths. These timings are not a controlled speedup claim.

Two issue prefixes were truncated in both arms. No source context required further token-budget truncation. The run demonstrates E2B inference on the user's T4, but no complete official repair score is available. For pydicom-1413, compatibility-adjusted SWE-bench 4.1.0 grading passed the reference fix (3/3 bug tests and 301/301 regression tests) and rejected the unfixed control. The original graph candidate failed all three bug tests while retaining 301 regression passes. All three conditions used pytest 7.4.4 to restore the historical tests' nose-style setup support. This single-case negative result is not a complete 23-task repair score. [T4 artifacts and audit](../evaluation/t4-e2b-nf4-v1/report.md).

## 5. Dataset and Release Scope

The current release contains original code and synthetic fixtures. It does not contain 80 additional repositories, temporal snapshots, real issue–patch trajectories or normalized competition assets.

A future dataset should record repository URL, exact commit, source license, parser configuration, label provenance and split assignment. Changed symbols can serve as localization labels, but are imperfect proxies for all context needed to solve an issue. Ambiguous examples require auditing.

The Apache-2.0 license covers original project code. External repository contents, embeddings and model weights retain their own terms. A toolkit license cannot assign redistribution rights to external assets.

## 6. Limitations

Python-only extraction and approximate call resolution limit graph coverage and correctness. Static dependencies can mislead retrieval. Whole-snippet packing may omit large relevant nodes. Source checking requires file reads and currently has no incremental rebuild mechanism. Character limits do not correspond exactly to model-token limits.

A Gemma E2B NF4 generation pilot has run on a T4, but the project has not established a 31B full-agent memory fit, tool-call reduction, lower peak memory or improved repair success. The observed millisecond retrieval timings apply only to the measured development snapshots and CPU runner.

The present resource needs independent test evaluation and official-data integration. Its current evidence supports a reproducible prototype, a small real-issue retrieval study and an E2B generation/application audit, not a state-of-the-art result.

## 7. Conclusion

LocalCodeGraph provides an offline foundation for bounded graph-assisted repository retrieval. Its present value is an inspectable implementation, explicit resource controls and a comparison workflow that preserves negative results. The public-development study shows mixed retrieval effects and no primary file-localization gain. Future work must establish whether revised policies improve localization and repair on independent repositories under realistic local-agent budgets.

## References

1. Liu et al. 2025. [CodexGraph: Bridging Large Language Models and Code Repositories via Code Graph Databases](https://aclanthology.org/2025.naacl-long.7/).
2. [RepoGraph: Enhancing AI Software Engineering with Repository-level Code Graph](https://arxiv.org/abs/2410.14684).
3. [LocAgent: Graph-Guided LLM Agents for Code Localization](https://arxiv.org/abs/2503.09089).
4. LocalCodeGraph. [Implementation and validation record, pull request 2](https://github.com/eluan216/LocalCodeGraph/pull/2); [CI run](https://github.com/eluan216/LocalCodeGraph/actions/runs/42325201898).
5. LocalCodeGraph. [SWE-bench Lite development study: results, protocol and reproduction](../evaluation/swebench-lite-dev-v1/report.md). Dataset: [SWE-bench Lite](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite).
6. Google. [Gemma 4 Developer Agent Paper Track](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper).

See references.bib for citation records. Complete author/venue metadata should be checked against the primary publications before final typesetting.

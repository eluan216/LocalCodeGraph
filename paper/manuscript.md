# LocalCodeGraph: A Lightweight, Offline Code-Graph Retrieval Toolkit

**Subtitle:** Budgeted repository context and reproducible evaluation for local software engineering agents

**Author:** eluan216 — replace with preferred publication name before submission  
**Affiliation and correspondence:** To be supplied by the author  
**Draft date:** November 7, 2026  
**Intended venue:** Google – The Gemma 4 Developer Agent Paper Track  
**Status:** Working resource-paper draft; real-world evaluation and competition integration are incomplete.

## Abstract

Repository navigation is a practical challenge for local software engineering agents. I present LocalCodeGraph, an offline Python toolkit for combining lexical retrieval, optional dense-vector retrieval and bounded code-graph expansion. The current implementation stores normalized snapshots in SQLite, extracts Python symbols with source locations, and searches identifiers using BM25 with naming-boundary normalization. Context selection combines rank fusion, dependency-weighted expansion, overlapping-source suppression and explicit traversal and output limits. Optional file-hash checks reject stale snippets. A comparison runner evaluates lexical and graph retrieval under matched context limits and retains per-task improvements and regressions.

The release includes source code, a command-line interface, synthetic fixtures, 17 automated tests and an evaluation protocol. On the included toy fixture, source deduplication reduces context from 540 to 291 characters relative to the preceding implementation; lexical and graph localization are tied. These observations establish functional behavior, not real-world retrieval superiority or improved repair success. Integration with official competition assets, a licensed extended dataset and full-model resource measurements remain planned. The resource is intended to make subsequent offline-agent experiments easier to inspect and reproduce.

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

These tests check implementation behavior. They do not estimate performance on natural issue descriptions.

### 4.2 Synthetic smoke observation

| Observation | Result | Interpretation |
| --- | --- | --- |
| Tests on each supported CI Python version | 17 passed | Functional validation |
| Toy context, preceding implementation | 540 characters | Included repeated module source |
| Toy context, revised implementation | 291 characters | Repeated source suppressed |
| Toy paired localization comparison | Tie | No measured localization improvement |

The context-size observation concerns one fixture and compares two implementation versions. It is not a comparison against a filesystem agent and does not measure tokens, tool calls, CPU/GPU memory or patch success.

### 4.3 Planned real-world study

The next evaluation will compare filesystem navigation, BM25, embedding-only retrieval and graph-assisted retrieval. Tasks must be pinned to pre-fix repository commits. Gold patches, test patches and localization labels must remain outside agent inputs.

The current runner compares BM25 and graph-assisted retrieval with the same character budget and result cap. The lexical arm can use all k lexical seeds; the graph arm reserves approximately half the slots for expansion. Both use the same context packer. This measures the incremental retrieval policy against an already structured packer, not against an unmodified general-purpose search engine.

The runner records Recall@k, reciprocal rank, predictions, output size, diagnostic latency and paired differences. Task-bootstrap intervals are descriptive; they do not correct for correlation between tasks from the same repository. Timing currently runs lexical retrieval before graph retrieval and can be affected by cache warming.

A full study should add repository-disjoint holdouts, repeated and randomized timing, actual tokenizer counts, resource measurements, closest feasible prior-work baselines and end-to-end patch validation with the same model and serving stack.

## 5. Dataset and Release Scope

The current release contains original code and synthetic fixtures. It does not contain 80 additional repositories, temporal snapshots, real issue–patch trajectories or normalized competition assets.

A future dataset should record repository URL, exact commit, source license, parser configuration, label provenance and split assignment. Changed symbols can serve as localization labels, but are imperfect proxies for all context needed to solve an issue. Ambiguous examples require auditing.

The Apache-2.0 license covers original project code. External repository contents, embeddings and model weights retain their own terms. A toolkit license cannot assign redistribution rights to external assets.

## 6. Limitations

Python-only extraction and approximate call resolution limit graph coverage and correctness. Static dependencies can mislead retrieval. Whole-snippet packing may omit large relevant nodes. Source checking requires file reads and currently has no incremental rebuild mechanism. Character limits do not correspond exactly to model-token limits.

No Gemma checkpoint has been evaluated through this toolkit. The project has not established a 16–24 GB full-agent memory fit, sub-50 ms query latency, tool-call reduction, lower peak memory or improved repair success. Those remain empirical questions.

The present resource needs real-world evaluation and official-data integration to support a competitive paper. Its current evidence supports a reproducible prototype, not a state-of-the-art result.

## 7. Conclusion

LocalCodeGraph provides an offline foundation for bounded graph-assisted repository retrieval. Its present value is an inspectable implementation, explicit resource controls and a comparison workflow that preserves negative results. Future work must establish whether these choices improve localization and repair on held-out repositories under realistic local-agent budgets.

## References

1. Liu et al. 2025. [CodexGraph: Bridging Large Language Models and Code Repositories via Code Graph Databases](https://aclanthology.org/2025.naacl-long.7/).
2. [RepoGraph: Enhancing AI Software Engineering with Repository-level Code Graph](https://arxiv.org/abs/2410.14684).
3. [LocAgent: Graph-Guided LLM Agents for Code Localization](https://arxiv.org/abs/2503.09089).
4. LocalCodeGraph. [Implementation and validation record, pull request 2](https://github.com/eluan216/LocalCodeGraph/pull/2); [CI run](https://github.com/eluan216/LocalCodeGraph/actions/runs/42325201898).
5. Google. [Gemma 4 Developer Agent Paper Track](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper).

See references.bib for citation records. Complete author/venue metadata should be checked against the primary publications before final typesetting.

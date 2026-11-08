# LocalCodeGraph

[Read the T4 v2 results and verified repair](evaluation/t4-e2b-nf4-v2/report.md) · [Colab setup and grading instructions](colab/README.md)

**I'm building an offline code-retrieval toolkit that helps local coding agents find useful repository context within a fixed budget.**

My goal is to make graph-assisted repository navigation practical for the Gemma 4 Developer Agent competition and useful beyond it. I combine lexical search, optional dense retrieval and bounded dependency expansion, without requiring a graph database server.

## Why I'm building this

Finding a matching function is only part of repository navigation. A fix may depend on a validator, caller or implementation elsewhere. Reading every matching file can exhaust an agent's context before it makes an edit.

I'm exploring a narrower question: **can I retrieve more of the right code than a BM25 baseline while keeping the output budget fixed?** I want the answer to come from reproducible comparisons, including cases where graph expansion hurts.

## What works today

| Capability | Current implementation |
| --- | --- |
| Repository indexing | Python AST extraction with source spans and file hashes |
| Graph storage | SQLite, atomic snapshot replacement, indexed incoming/outgoing edges |
| Lexical retrieval | BM25 with snake_case, camelCase and acronym splitting |
| Semantic retrieval | Optional chunked cosine search over memory-mapped NumPy embeddings |
| Context selection | Rank fusion, dependency-weighted expansion, overlapping-snippet suppression |
| Resource controls | Character budget, result cap, traversal cap, hop and neighbor limits |
| Freshness | Optional source-hash verification that rejects stale or unverifiable snippets |
| Evaluation | Budget-matched BM25 comparison, per-task wins/losses, paired bootstrap intervals |

The core runs without third-party runtime dependencies. Dense search requires NumPy and compatible vectors supplied by the user.

## Try it

Python 3.10+ and SQLite with FTS5:

```bash
git clone https://github.com/eluan216/LocalCodeGraph.git
cd LocalCodeGraph
python -m pip install -e .

lcg --db demo.sqlite index examples/toy_repo
lcg --db demo.sqlite search "decode input"
lcg --db demo.sqlite context "decode input" --max-chars 8000
```

To reject context whose source files have changed since indexing:

```bash
lcg --db demo.sqlite context "decode input" --root examples/toy_repo
```

Reindex after source changes. Freshness checking rejects stale snippets; it does not rebuild the graph automatically.

## Use it from Python

```python
from localcodegraph import GraphStore
from localcodegraph.retrieval import context_for_task

with GraphStore("demo.sqlite") as graph:
    result = context_for_task(
        graph,
        "decode input",
        max_chars=8000,
        max_results=10,
        max_nodes=30,
        root="examples/toy_repo",
    )
    print(result["context"])
    print(result["skipped"])
```

For dense retrieval, install `pip install -e ".[dense]"`. Supply a floating-point vectors.npy matrix, a JSON list of node IDs in row order, and query vectors from the same encoder/revision/preprocessing. Use DenseIndex.search_vector and pass its ranked results as dense_hits to context_for_task.

## How I compare against the baseline

My current reference baseline is **BM25 retrieval with the same context packer, character budget and result cap**. The graph condition reserves some retrieval slots for dependencies. Both conditions use the same snapshot and queries.

```bash
python -m localcodegraph.evaluation   --db demo.sqlite   --tasks examples/tasks.jsonl   --mode compare   -k 10   --max-chars 8000   --output comparison.json

python -m unittest discover -s tests -v
```

The report includes Recall@k, MRR, selected node IDs, context size, retrieval latency, paired recall differences, wins, losses, ties and a seeded task-bootstrap interval.

### Real-world development results

I evaluated all 23 public SWE-bench Lite development tasks across six repositories, using each task's pre-fix commit. Both arms used the same 8,000-character and ten-node output caps.

| Metric | BM25 + common packer | Graph + common packer |
| --- | ---: | ---: |
| Changed-file hits | 11/23 (47.8%) | 11/23 (47.8%) |
| Exploratory symbol-proxy recall, 22 labeled tasks | 22.7% | 27.3% |
| Median context characters | 6,008 | 7,902 |
| Median diagnostic retrieval latency | 12.36 ms | 12.88 ms |

The primary result is a tie, with one graph win and one loss. The symbol-proxy gain comes from one task; the graph arm also uses more context and is slightly slower. I have not established superiority over BM25, the official Kaggle baseline, LocAgent, RepoGraph or a leaderboard entry.

[Read the full evaluation, limitations and reproduction steps](evaluation/swebench-lite-dev-v1/report.md), [inspect every prediction](evaluation/swebench-lite-dev-v1/results.json), or [view the successful run](https://github.com/eluan216/LocalCodeGraph/actions/runs/42326138785). This is a CPU retrieval study on a public development set, not a Gemma repair experiment. The next milestone is a stronger lexical oversampling baseline and an independent frozen test set.

### Observed Gemma repair pilot on a free T4

I ran Gemma 4 E2B with NF4 quantization on all 23 development tasks in both conditions: 46 completed attempts. Graph context produced 10 parser-accepted patches versus 4 for BM25. Ordinary application checks found one graph patch that changed source and none for BM25; two other applicable exports were no-ops.

I tested the source-changing graph candidate with reference-fix and unfixed controls. The controls behaved correctly, but the generated patch failed all three bug tests. This establishes T4 feasibility for this E2B configuration and identifies unreliable patch generation as the main bottleneck. It does not establish a repair improvement or validate the 31B checkpoint.

[Full T4 results, memory observations, failure analysis and controlled tests](evaluation/t4-e2b-nf4-v1/report.md).

### Structured-edit v2: one verified BM25 repair after revalidation

I completed all 23 tasks per arm, with two generations each. The original strict
JSON parser rejected all 46 attempts. I preserved those outcomes, then independently
revalidated the saved final responses with a single-JSON-fence allowance.

| Post-hoc final outcome | BM25 | Graph |
| --- | ---: | ---: |
| Applicable patches | 2 | 0 |
| Abstentions | 7 | 6 |
| Validation/generation errors | 14 | 17 |

The pydicom-1694 BM25 candidate passed its bug test and all 26 labeled regression
tests. The SQLFluff-2419 candidate failed its bug test. Both reference-fix and
unfixed controls behaved correctly. SQLFluff has no labeled regression tests for
this task. These are controlled candidate results, not a full official repair score.

[Read the complete v2 report and controls](evaluation/t4-e2b-nf4-v2/report.md).
This gives me one test-verified E2B repair on a free T4 after post-hoc normalization;
it does not show a graph advantage. The original v2 exports remain empty.

The separately labeled v3 prompt removes the example path and directs edits to
pre-fix source headers. It has no GPU result yet. The
[frozen 12-task holdout](benchmarks/repair-holdout-v1.json) remains reserved until
the development policy is finalized.

## Design choices

- I prioritize calls and references over broad containment links.
- I downweight whole-file/module snippets and suppress nested snippets that repeat source already selected.
- I keep semantic retrieval optional so lexical and graph retrieval work without an embedding model.
- I return source locations, selection scores and skipped-node reasons so retrieval decisions can be inspected.
- I keep the standalone toolkit separate from the competition adapter until the official assets and harness have been validated.

## Current limits

The parser supports Python. Call links are approximate and do not model assignments, cross-file imports or dynamic dispatch. Node IDs are specific to a snapshot. Context budgets count characters, not Gemma tokens. Graph expansion can retrieve irrelevant dependencies and can lose to lexical search.

I have not measured full-model memory requirements, released an extended real-world dataset, or produced a validated competition submission.zip. The JSON importer accepts the documented normalized format; it does not yet ingest the competition's raw files directly.

## Research and development

- [Research review and public competition work](docs/research.md)
- [Evaluation protocol and limitations](docs/evaluation.md)
- [Snapshot interchange format](docs/schema.md)
- [Competition integration status](competition/README.md)
- [Roadmap](docs/roadmap.md)

I build on [CodexGraph](https://arxiv.org/abs/2408.03910), [RepoGraph](https://github.com/ozyyshr/RepoGraph) and [LocAgent](https://github.com/gersteinlab/LocAgent). My intended contribution is a usable, resource-conscious retrieval and evaluation toolkit. Storage choices alone are not a claim of research novelty.

## License

I'm releasing the original project code under Apache-2.0. External code repositories, datasets, embeddings and model weights retain their own licenses.

# SWE-bench Lite development evaluation v1

Run date: November 7, 2026. **This run does not establish an overall graph-retrieval improvement.**

## Scope and provenance

All 23 public development tasks from six repositories completed, with no task exclusions or execution failures. Each task used its exact pre-fix base commit. The immutable dataset revision is 6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2. The parquet SHA256, source-archive hashes, task IDs, base commits and predictions are in [results.json](results.json).

The protocol was committed before the run: [protocol](../../benchmarks/PROTOCOL.md), [implementation commit](https://github.com/eluan216/LocalCodeGraph/commit/db6d1874e2e8920b45112da5bf86bf79629ccbfa), [successful run](https://github.com/eluan216/LocalCodeGraph/actions/runs/42326138785). Predictions were generated before reading reference patches for labels. Target repository code was parsed, never executed. Source code and issue bodies are not copied into this result release.

This is a public-development retrieval study, not a blind held-out experiment, a Gemma run, or an official SWE-bench/Kaggle repair score.

## Conditions

Both arms used the current identifier-aware BM25 index, the same source-deduplicating context packer, an 8,000-character output cap, at most 10 emitted nodes and a 30-visited-node ceiling. BM25 used 10 lexical seeds and no expansion. Graph retrieval used five lexical seeds, one-hop fixed-weight expansion and at most 20 neighbors per expansion. Neither arm used dense embeddings.

Each deterministic query ran three times with alternating arm order. Timing reports the median within each task, then the median across tasks. These are warm-process diagnostic timings, not a cold-start or hardware-controlled latency study.

## Measured results

| Metric | BM25 + common packer | Graph + common packer |
| --- | ---: | ---: |
| Mean changed-file recall | 47.83% | 47.83% |
| Tasks with a changed-file hit | 11/23 | 11/23 |
| File MRR | 0.4130 | 0.4130 |
| Exploratory symbol-proxy recall, 22 labeled tasks | 22.73% | 27.27% |
| Median context characters | 6,008 | 7,902 |
| Median retrieval latency | 12.36 ms | 12.88 ms |

Every task in this split has one changed source path, so file recall and file hit rate coincide. All changed files were indexed. Five source files across all snapshots were skipped by the parser; paths and reasons are retained in the raw records.

The primary paired recall difference is **0.00 percentage points**. The seeded 2,000-resample task-bootstrap 95% interval is [-13.04, +13.04] points; the repository-cluster interval is [-12.50, +12.50] points. There is one win, one loss and 21 ties. These wide intervals do not establish equivalence or superiority.

The graph arm's median context is 31.5% larger and its diagnostic median retrieval latency is 4.2% higher. These are ratios of the reported medians, not median paired changes. No tool-call, token, patch-success or GPU-memory measurement was made.

## Repository breakdown

| Repository | Tasks | BM25 file hits | Graph file hits |
| --- | ---: | ---: | ---: |
| marshmallow-code/marshmallow | 2 | 0 | 0 |
| pvlib/pvlib-python | 5 | 4 | 5 |
| pydicom/pydicom | 5 | 2 | 2 |
| pylint-dev/astroid | 5 | 2 | 1 |
| pyvista/pyvista | 1 | 1 | 1 |
| sqlfluff/sqlfluff | 5 | 2 | 2 |

## Cases that explain the aggregate

- pvlib__pvlib-python-1072: the graph arm retrieved helpers in pvlib/temperature.py and gained a file hit, but did not retrieve the labeled fuentes function. A file hit does not guarantee the relevant implementation was returned.
- pylint-dev__astroid-1333: BM25 retrieved astroid/modutils.py; graph retrieval instead filled most of its budget with doc/conf.py and lost the file hit. Reserving seeds for expansion can discard useful lexical candidates.
- pyvista__pyvista-4315: both arms retrieved the right file, while graph expansion additionally retrieved the labeled RectilinearGrid initializer. This is the only task contributing to the observed symbol-proxy gain.

## Resource observations

The runner used Linux x86_64, Python 3.12.16 and four reported CPUs. Median indexing time was 0.711 seconds (maximum 1.664 seconds); median SQLite size was 11.08 MiB (maximum 27.14 MiB). Snapshots contained 1,331–5,413 nodes. Indexing times exclude downloading and archive extraction. These figures apply to this development set and runner.

The raw Linux ru_maxrss value is exactly 139,776 KiB for every worker. Subprocess high-water RSS can reflect the launch environment; this constant reading is not treated as an isolated toolkit-memory estimate. It cannot support a memory-reduction or model-co-residency claim.

## Interpretation and limitations

This run supports a narrow conclusion: the graph policy occasionally changes which useful context is returned, but it did not improve primary file localization over the configured lexical baseline. The exploratory symbol gain rests on one task and is not evidence of a reliable general effect.

Both arms share a custom packer, so this is an incremental-policy comparison. The baseline inspects only ten lexical seeds, while the graph arm can visit additional structural candidates. A stronger lexical oversampling baseline is needed to separate structural value from candidate-pool and packing effects. No retrieval settings were changed after these scores.

Symbol labels are heuristic: the smallest pre-fix function/method intersecting removed lines or insertion anchors. They can miss new functions, module-level changes or necessary unchanged context. One task has no symbol label. These labels have not been manually audited and are secondary to changed-file localization.

Other limits include a small public development split, correlated tasks within six projects, same-file approximate call links, query truncation to the existing searcher's first 64 normalized unique terms, static source analysis and only one hosting environment. The current packer can underfill a budget by rejecting large snippets. Results must not be generalized to all repositories, Gemma behavior or repair performance.

## Reproduction

```bash
git clone https://github.com/eluan216/LocalCodeGraph.git
cd LocalCodeGraph
git checkout db6d1874e2e8920b45112da5bf86bf79629ccbfa
python -m pip install -e . pyarrow==26.0.1 unidiff==1.0.1
python benchmarks/run_swebench_lite.py \
  --revision 6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2 \
  --output results/real-world.json
```

Use Linux and Python 3.12 for the resource API. Downloads require internet; indexing and retrieval themselves do not. Reproduction executes the retrieval study only. Historical source parsing may vary across Python versions. External source repositories and SWE-bench assets retain their own terms.

## Paper-ready result paragraph

On all 23 public SWE-bench Lite development tasks spanning six repositories, graph-assisted retrieval and the configured BM25 baseline each achieved 47.8% changed-file recall under an 8,000-character and ten-node output cap. The graph arm gained one task and lost one; the paired mean difference was zero, with a repository-cluster bootstrap 95% interval of -12.5 to +12.5 percentage points. Exploratory changed-symbol proxy recall increased from 22.7% to 27.3% over 22 labeled tasks, attributable to one example. Median context size increased from 6,008 to 7,902 characters and median diagnostic retrieval latency from 12.36 to 12.88 ms. These findings do not establish overall superiority and motivate stronger lexical baselines and an independent evaluation set.

# Evidence ledger — Paper Track submission (11 November 2026)

This ledger tracks claims. Only statements with evidence below are asserted in the submitted writeup.

| Proposed claim | Current evidence | Status for submission |
| --- | --- | --- |
| 35–60% fewer tool calls / 48% median reduction | None | **Not claimed** |
| 40–41% lower peak memory | None | **Not claimed** |
| 11–17 point localization gain | None | **Not claimed** |
| Full model and retrieval fit 16–24 GB | None | **Not claimed** |
| 80 public repositories and temporal snapshots released | Not collected | **Not claimed** |
| Multi-language tree-sitter parser | Python AST only | **Not claimed** |
| Official raw-asset ingestion | Normalized JSON importer only | **Not claimed** |
| Exact harness tools and ADK skills | Standalone APIs only | **Not claimed** |
| Under 50 ms queries / two-minute construction | Not measured on competition hardware | **Not claimed** |
| All artifacts Apache-2.0 | Original code only | Stated with external-license caveat |
| 17 automated tests passed on Python 3.10/3.12 | CI run 42325201898 | **Claimed** |
| Toy context 540 to 291 characters | Before/after CI logs | **Claimed** (fixture only) |
| Changed-file recall 47.83% (11/23) both arms | evaluation/swebench-lite-dev-v1 | **Claimed** |
| Symbol-proxy recall 22.73% → 27.27% | evaluation/swebench-lite-dev-v1 | **Claimed** (single-task dependent) |
| One post-hoc test-verified BM25 repair (pydicom-1694) | evaluation/t4-e2b-nf4-v2 | **Claimed** |
| No graph candidate survived post-hoc validation | evaluation/t4-e2b-nf4-v2 | **Claimed** |

## Completed real-issue development study (2026-11-07)

All 23 SWE-bench Lite dev tasks completed across six repositories at exact pre-fix commits. BM25 and graph each achieved 47.83% changed-file recall (11/23); the paired difference was zero, with a repository-cluster bootstrap interval of -12.5 to +12.5 percentage points.

Exploratory symbol-proxy recall was 22.73% versus 27.27% on 22 labeled tasks. This gain depends on one task and does not validate any larger localization claim. Graph context and diagnostic retrieval latency were larger.

[Raw predictions and full limitations](../evaluation/swebench-lite-dev-v1/report.md). No Gemma, tool-call, GPU-memory or repair-success claims are supported by this study.

## Observed T4 generation and controlled grading (2026-11-07)

The E2B base checkpoint with NF4 quantization completed 46 attempts (23 per arm) on a free Colab T4. Parser acceptance was BM25 4/23 and graph 10/23. Ordinary application with actual source changes was 0/23 and 1/23. The graph candidate failed all three bug tests in compatibility-adjusted controlled grading; reference and unfixed controls behaved correctly. No complete official repair score is reported.

Maximum saved PyTorch reserved readings were 7.64/7.77 GiB; these are not total GPU memory, a baseline memory reduction or evidence that 31B fits. [Full protocol and evidence](../evaluation/t4-e2b-nf4-v1/report.md).

## Structured-edit v2 and post-hoc controlled tests (2026-11-08)

All 46 original v2 attempts failed under strict JSON parsing (92 generations).
Independent final-step-only revalidation, allowing one JSON fence with all source
checks retained, recovered two BM25 candidates and no graph candidates.

Pydicom-1694 passed one bug test and all 26 labeled regression tests with qualified
reference/unfixed controls. SQLFluff-2419 failed its one bug test with qualified
controls; that task has no labeled regression tests. This is one post-hoc
test-verified BM25 repair, not an original v2 success, a complete official repair
score, a graph improvement, 31B evidence or independent holdout performance.
[Reproduction, raw attempts and machine-readable controls](../evaluation/t4-e2b-nf4-v2/report.md).

## Submission note (11 November 2026)

The Kaggle Writeup is the content of `paper/WRITEUP.md` (identical body to the finalized manuscript). Public artifacts are the repository itself and the three evaluation report directories. No unsupported numerical claims appear in the submitted text.

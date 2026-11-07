# Evidence needed before submission

This ledger tracks claims in the initial concept draft. It is not a results table.

| Proposed claim | Current evidence | Required next step |
| --- | --- | --- |
| 35–60% fewer tool calls / 48% median reduction | None | Paired full-agent traces with a fixed model, budget and task set |
| 40–41% lower peak memory | None | Define CPU/GPU metric and baseline; record comparable peak measurements |
| 11–17 point localization gain | None | Audited held-out labels, matched baselines, uncertainty and per-task results |
| Full model and retrieval fit 16–24 GB | None | Measure model weights, KV cache, runtime overhead and index separately |
| 80 public repositories and temporal snapshots released | Not collected | Licensed manifest, exact commits, audited labels and accessible artifacts |
| Multi-language tree-sitter parser | Python AST only | Implement and validate language-specific extraction and resolution |
| Official raw-asset ingestion | Normalized JSON importer only | Inspect actual schemas and test adapters |
| Exact harness tools and ADK skills | Standalone APIs only | Validate registered-tool interfaces and sandbox execution |
| Under 50 ms queries / two-minute construction | Not measured | Pinned corpus and hardware; cold/warm repeated timing |
| All artifacts Apache-2.0 | Original code only | Track external asset terms individually |
| 17 automated tests passed on Python 3.10/3.12 | CI run 42325201898 | Preserve commit/run provenance |
| Toy context 540 to 291 characters | Before/after CI logs | Limit statement to this fixture and duplicated-source removal |

The manuscript date reflects the current draft, November 2026, rather than backdating work to September. Author identity, affiliation and correspondence remain author-supplied fields.

Do not submit this working paper as a completed empirical study. The next milestone is reliable source edits and independent end-to-end repair evaluation; a larger corpus is useful only if its provenance and evaluation quality are credible.

## Completed real-issue development study (2026-11-07)

All 23 SWE-bench Lite dev tasks completed across six repositories at exact pre-fix commits. BM25 and graph each achieved 47.83% changed-file recall (11/23); the paired difference was zero, with a repository-cluster bootstrap interval of -12.5 to +12.5 percentage points.

Exploratory symbol-proxy recall was 22.73% versus 27.27% on 22 labeled tasks. This gain depends on one task and does not validate the proposed 11–17 point claim. Graph context and diagnostic retrieval latency were larger.

[Raw predictions and full limitations](../evaluation/swebench-lite-dev-v1/report.md). No Gemma, tool-call, GPU-memory or repair-success claims are supported by this study. The constant raw ru_maxrss readings are retained but not used as isolated toolkit-memory evidence.

## Observed T4 generation and controlled grading (2026-11-07)

The E2B base checkpoint with NF4 quantization completed 46 attempts (23 per arm) on the user's free Colab T4. Parser acceptance was BM25 4/23 and graph 10/23. Ordinary application with actual source changes was 0/23 and 1/23. The graph candidate failed all three bug tests in compatibility-adjusted controlled grading; reference and unfixed controls behaved correctly. No complete official repair score is reported.

Maximum saved PyTorch reserved readings were 7.64/7.77 GiB; these are not total GPU memory, a baseline memory reduction or evidence that 31B fits. [Full protocol and evidence](../evaluation/t4-e2b-nf4-v1/report.md).

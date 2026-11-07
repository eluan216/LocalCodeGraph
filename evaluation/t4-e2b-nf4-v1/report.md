# Gemma E2B NF4 on the user's free Colab T4

## Scope and provenance

This is an observed GPU generation pilot, not a completed official SWE-bench or Kaggle repair score. The user supplied all 46 saved attempts and two 23-task prediction files from toolkit commit 2011ec10664bec98879a36d5f7ae3e96fd2e7b8f. Exported patches exactly match their saved attempt records. Raw private transfer links and environment dumps are omitted.

Base weights: google/gemma-4-E2B-it, revision 4adf15748de9e1a0097b6274cee9c15836c41c37. Runtime: PyTorch 2.14.1+cu130, Transformers 5.22.2, bitsandbytes 0.50.2, Accelerate 1.15.0. The run used NF4 double quantization, FP16 compute, eager attention and greedy decoding, with a 4,096-token prompt cap and 1,024-token output cap. It is not the official W4A16 QAT checkpoint and cannot validate 31B performance.

All 23 SWE-bench Lite public dev tasks were attempted in both arms. Two issue descriptions were truncated to the shared prefix cap in both arms; no source context was further truncated by the token packer. See generation-summary.json for full settings and input provenance.

## Observed generation and applicability

| Metric | BM25 context | Graph context |
| --- | ---: | ---: |
| Planned/completed attempts | 23/23 | 23/23 |
| Generator parser accepted | 4 | 10 |
| Generator errors | 19 | 13 |
| Ordinary git apply check passes | 1 | 2 |
| Applies and changes source | 0 | 1 |
| Median generation seconds | 21.78 | 20.59 |
| Median input tokens | 2,118 | 2,770 |
| Median output tokens | 186 | 180 |
| Maximum PyTorch allocated GiB | 7.35 | 7.49 |
| Maximum PyTorch reserved GiB | 7.64 | 7.77 |

Memory figures are allocator/reservation readings saved per generation, not total device memory. The hardware snapshot confirms a Tesla T4 with 15,360 MiB and was captured after inference ended. These observations show this E2B configuration ran on the user's T4; they imply nothing about the 31B checkpoint.

Total recorded generation time is 830.21 seconds for BM25 and 571.10 seconds for graph, excluding model loading/preparation. Differences in output lengths and two BM25 output-limit failures affect timing; the totals are not a controlled retrieval-speed improvement.

Most errors were malformed unified diffs: 24 incorrect-length hunks, two unexpected hunk headers and four stray-fence errors. Two BM25 attempts hit the output cap. No saved attempt reports a GPU out-of-memory or CUDA exception.

## Application audit

The original 14 nonempty exports were checked on exact pre-fix Python snapshots using ordinary git apply, without changing hunk counts, repairing output or executing project code. Source archive hashes and diagnostics are retained in application-audit.json. [Audit run](https://github.com/eluan216/LocalCodeGraph/actions/runs/42374211276).

BM25's sole applicable export (astroid-1333) made no worktree change. Graph's sqlfluff-2419 export also made no change. The graph export for pydicom-1413 applied and changed pydicom/util/codify.py; this does not establish that it fixes the issue.

The generator's original patch status was too permissive: its diff parser accepted unchanged edits and some trailing material. Those statuses are preserved as original observations, not retroactively relabeled as valid repairs.

Strict application is an additional audit, not the full official harness: an official grader may have different fallback patch-application behavior. No full-suite repair rate is inferred from these checks.

## Test-based verification

I graded pydicom-1413 using SWE-bench 4.1.0 in Docker against the pinned development task. The initial reference control exposed a historical-test compatibility problem: pytest 8.4.2 no longer ran the class's nose-style setup method, causing two unrelated AttributeError failures. I pinned pytest 7.4.4 identically for every condition; no generated patch was changed.

| Condition | Bug tests passing | Regression tests passing | Resolved |
| --- | ---: | ---: | --- |
| Reference fix | 3/3 | 301/301 | Yes |
| Unfixed program control | 0/3 | 301/301 | No |
| Original graph candidate | 0/3 | 301/301 | No |

The unfixed control adds only a marker file so the harness executes tests instead of skipping an empty patch. Both controls validate this single-case comparison. The generated edit to codify.py does not fix the reported bug. This is one tested candidate, not a complete official 23-task repair score. Other parser/application failures were not all graded by the harness.

[Controlled grading run](https://github.com/eluan216/LocalCodeGraph/actions/runs/42375703225), [machine-readable controls](grading-controls.json). The harness dependency override is explicitly recorded; these are compatibility-adjusted results.

## Interpretation

Graph context increased parser acceptance in this small pilot, but that gain largely disappears when checking applicability and actual source changes. The main demonstrated bottleneck is patch-generation reliability, not GPU capacity. The next engineering step should validate structured edits against exact source and render diffs deterministically, while retaining this original run unchanged. Any revised generation protocol needs a separately labeled experiment and independent validation.

This public dev set has already been analyzed. It is not an independent holdout. No claim of general superiority, competition score or 31B repair performance is supported.

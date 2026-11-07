# Run my structured-edit repair pilot on a free Colab T4

[Open the v2 notebook](https://colab.research.google.com/github/eluan216/LocalCodeGraph/blob/main/colab/LocalCodeGraph_Gemma_Repair_v2.ipynb)

My next run uses validated JSON replacements and Python-generated diffs, with one
correction after a validation failure. It keeps the v1 model revision and token caps,
and saves results to /content/lcg-t4-v2-run. Run all cells in order in a T4 runtime.
The preparation cell downloads hash-verified pre-fix snapshots for offline validation.
It never executes repository code or supplies reference fixes to the model.

If the same runtime still has the v1 inputs and model, the v2 notebook reuses them.
A changed backend or protocol cannot be resumed into an existing v2 run.
Download the v2 ZIP after completion or interruption. Share that ZIP through Drive
as before; it includes every response and failure. Test grading happens separately.

The v1 run completed on your T4. Its graph candidate failed controlled bug tests;
[observed results](../evaluation/t4-e2b-nf4-v1/report.md). V2 has CPU validation only
until a new GPU run is completed. Do not rerun v1 expecting the structured-edit change.

[V2 frozen protocol](../benchmarks/T4_REPAIR_V2_PROTOCOL.md). Both arms can use two
generations, so report total tokens, latency and retries. V1-versus-v2 is a development
comparison with changed format and retry budget, not an isolated graph improvement.

## Frozen holdout

[Open the 12-task holdout notebook](https://colab.research.google.com/github/eluan216/LocalCodeGraph/blob/main/colab/LocalCodeGraph_Gemma_Repair_Holdout.ipynb).

The [frozen manifest](../benchmarks/repair-holdout-v1.json) selects three tasks each
from Django, Matplotlib, scikit-learn and SymPy using task-ID hashes. These repositories
are outside the analyzed development set. Use this only after finalizing v2; keep
all 12 planned tasks per arm, including failures, and do not tune on the results.
The public benchmark may have appeared in model pretraining.

## Original v1 instructions


[Open the T4 notebook](https://colab.research.google.com/github/eluan216/LocalCodeGraph/blob/main/colab/LocalCodeGraph_Gemma_Repair.ipynb)

The default notebook now targets the T4 GPU available in free Colab. It uses **google/gemma-4-E2B-it with bitsandbytes NF4 quantization and FP16 compute**, without vLLM or a paid API.

This is a separate E2B development experiment. It does not use the 31B model or the competition's official W4A16 QAT weights. Results must be labeled E2B NF4 and cannot be presented as 31B results.

## Run it

1. Select Runtime → Change runtime type → T4 GPU.
2. Run cells in order. The notebook checks for approximately 15 GiB GPU memory and initial disk space.
3. If Hugging Face requests authentication, put HF_TOKEN in Colab Secrets, not in source code.
4. Save the output ZIP, including partial work if interrupted.
5. Grade generated patches separately with the official SWE-bench Docker harness.

No A100 or paid service is required by this configuration. Free GPU access/session duration still depend on Colab availability. The notebook and controller have CPU validation; the completed v1 observations are linked above.

## T4 settings

| Setting | Value |
| --- | --- |
| Base model | Gemma 4 E2B instruction-tuned |
| Quantization | bitsandbytes NF4, double quantization |
| Compute | FP16; no BF16 requirement |
| Backend | Transformers + eager attention |
| Input cap | 4,096 tokens |
| Shared issue-prefix cap | 1,536 tokens |
| Output cap | 1,024 tokens |
| Sampling | Greedy, seed zero |
| Population | All 23 public SWE-bench Lite dev tasks |
| Arms | BM25 context and graph context |

The original source contexts are capped at 8,000 characters. The T4 prompt builder trims context further when needed to meet the token limit and records truncation. Both arms retain the same issue prefix and instructions.

The installer uses an isolated virtual environment with access to Colab's existing PyTorch/CUDA packages. Resolved package versions, hardware, model revision/config hash and input checksum are recorded.

## Interruption and resume

Every completed attempt is atomically checkpointed in attempts/. Prediction files are rebuilt after each attempt. Run the notebook's download cell to save partial outputs before leaving.

To continue on the same runtime with the same files/settings, set RESUME=True and rerun. Existing attempts—including errors—are skipped, not retried. Changed input/model/backend-version manifests cannot be mixed into an existing run. Files can disappear when a Colab VM is deleted; resume does not recover files that were never saved.

## Outputs

- predictions.bm25.jsonl and predictions.graph.jsonl: SWE-bench prediction records labeled E2B NF4.
- attempts/: individual responses, errors, input/output token counts and prompt hashes.
- manifest.json: experiment settings, model revision/config hash, backend versions, input manifest and task IDs.
- environment.txt, hardware.txt and toolkit-commit.txt: runtime provenance.
- gold-free-inputs/: exact issue/context inputs and upstream license notices.

PyTorch peak allocated/reserved memory is recorded per successful generation. It is not total GPU device memory. Diff parsing is not correctness verification.

## Test-based grading

Use the [official SWE-bench harness](https://github.com/SWE-bench/SWE-bench) on a Docker-capable host. Pin its revision and confirm the CLI flags before running:

```bash
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Lite --split dev \
  --predictions_path predictions.bm25.jsonl \
  --max_workers 2 --run_id lcg-t4-e2b-dev-bm25-v1

python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Lite --split dev \
  --predictions_path predictions.graph.jsonl \
  --max_workers 2 --run_id lcg-t4-e2b-dev-graph-v1
```

Keep the dataset/base commits aligned with the input manifest. Use unique run IDs, validate gold-patch and genuinely unfixed-source controls, and retain missing/error reports. An empty-patch skip is not an unfixed-source test control. A complete paired study needs all 23 planned tasks in both arms.

This is one-shot patch generation, not the multi-turn ADK competition agent. Test grading remains separate from Colab inference. The completed v1 pilot and its negative single-case test result are linked above.

## Archived 31B setup

The original large-GPU notebook is preserved as [Gemma_31B_Large_GPU.ipynb](Gemma_31B_Large_GPU.ipynb). It is not intended for your free T4 and is not the default link.

## Sources and protocol

- [T4 experiment protocol](../benchmarks/T4_REPAIR_PROTOCOL.md)
- [31B experiment protocol](../benchmarks/REPAIR_PROTOCOL.md)
- [Official E2B model](https://huggingface.co/google/gemma-4-E2B-it)
- [Bitsandbytes hardware requirements](https://huggingface.co/docs/transformers/quantization/bitsandbytes)
- [Colab resource limits](https://research.google.com/colaboratory/faq.html)

### Audio attention startup fix

The previous global SDPA setting failed during Gemma4AudioModel initialization. The loader now uses eager attention, as recommended by the Transformers error. On --resume, only an otherwise identical startup manifest with no attempts/predictions can be corrected; the original manifest is archived. Existing attempts are never rewritten or mixed with changed settings.

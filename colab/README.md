# Run my Gemma repair pilot on a free Colab T4

[Open the T4 notebook](https://colab.research.google.com/github/eluan216/LocalCodeGraph/blob/main/colab/LocalCodeGraph_Gemma_Repair.ipynb)

The default notebook now targets the T4 GPU available in free Colab. It uses **google/gemma-4-E2B-it with bitsandbytes NF4 quantization and FP16 compute**, without vLLM or a paid API.

This is a separate E2B development experiment. It does not use the 31B model or the competition's official W4A16 QAT weights. Results must be labeled E2B NF4 and cannot be presented as 31B results.

## Run it

1. Select Runtime → Change runtime type → T4 GPU.
2. Run cells in order. The notebook checks for approximately 15 GiB GPU memory and initial disk space.
3. If Hugging Face requests authentication, put HF_TOKEN in Colab Secrets, not in source code.
4. Save the output ZIP, including partial work if interrupted.
5. Grade generated patches separately with the official SWE-bench Docker harness.

No A100 or paid service is required by this configuration. Free GPU access/session duration still depend on Colab availability. The notebook and controller have CPU validation; actual E2B fit and speed need your T4 runtime test.

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

This is one-shot patch generation, not the multi-turn ADK competition agent. Test grading remains separate from Colab inference. No Gemma repair result has been measured yet.

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

# Run my Gemma repair pilot in Google Colab

[Open the notebook in Colab](https://colab.research.google.com/github/eluan216/LocalCodeGraph/blob/main/colab/LocalCodeGraph_Gemma_Repair.ipynb)

I use this notebook to compare one-shot Gemma patches produced from BM25 and graph context on all 23 SWE-bench Lite development tasks. This is a pilot, not a scored competition submission or a verified repair result.

## What you need

- A Colab GPU with at least 38,000 MiB of VRAM; select an A100-class runtime. The notebook deliberately stops on a free 16 GB T4.
- At least 65 GiB free disk and enough runtime to download the model and complete 46 generation requests.
- Internet for installation, source preparation and the model download. Inference runs against a local-only endpoint.

Colab GPU types and availability are not guaranteed, even with paid plans. This notebook does not buy compute. [Colab FAQ](https://research.google.com/colaboratory/faq.html).

## Run it

1. Open the notebook and choose the GPU runtime.
2. Run cells in order. The initial GPU/disk checks happen before large downloads.
3. If Hugging Face requests authentication, use Colab Secrets with the name HF_TOKEN. Never put a token into source code.
4. Download the output ZIP before the runtime disconnects.
5. Grade both prediction files on a separate Docker-capable host.

The notebook isolates model dependencies in a virtual environment, pins vLLM 0.30.0, records the immutable model revision, hashes local weight/config files, preserves errors and avoids overwriting prior outputs. CPU CI tests notebook code syntax and controller plumbing; GPU compatibility still needs an actual Colab run.

## Output files

- predictions.bm25.jsonl and predictions.graph.jsonl: official SWE-bench prediction fields.
- traces.jsonl: raw model responses, completion status, usage and request hashes.
- manifest.json: task IDs, input checksum, model revision and model-file hashes.
- environment.txt, hardware.txt, toolkit-commit.txt and vllm.log: runtime provenance.
- gold-free-inputs/: exact prompts/context inputs, checksum manifest and upstream license files.

Patch parsing only establishes diff syntax and the pilot's path policy. It does not establish applicability, correctness or test success.

## Grade on a Docker-capable machine

Use a pinned checkout/version of the [official SWE-bench harness](https://github.com/SWE-bench/SWE-bench), record that revision and verify its CLI help before running. The documented compatibility entry point is:

```bash
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Lite --split dev \
  --predictions_path predictions.bm25.jsonl \
  --max_workers 2 --run_id lcg-gemma-dev-bm25-v1

python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Lite --split dev \
  --predictions_path predictions.graph.jsonl \
  --max_workers 2 --run_id lcg-gemma-dev-graph-v1
```

Use separate new run IDs to prevent cached reports from being reused. Confirm the grader resolves the same dataset revision/base commits recorded in the input manifest; stop if they differ. Before interpreting model scores, validate gold-patch controls and genuinely unfixed-source controls. An empty-patch prediction may be skipped by the grader and is not an unfixed-source control.

Colab inference is separate from Docker test verification; this notebook does not attempt to bypass managed-runtime container restrictions. [Official evaluation guide](https://www.swebench.com/SWE-bench/guides/evaluation/).

## Experiment boundaries

Both arms use the same checkpoint, issue and decoding settings. Only context differs. No reference/test patch or expected outcome is passed to Gemma. There is no best-of selection or retry loop. This is a one-shot context-to-patch experiment, not the multi-turn ADK harness.

The dev set has already informed retrieval analysis. Any improvement observed here must be checked on an independent frozen test set before a general claim. No Gemma repair performance has yet been measured.

See [the frozen repair protocol](../benchmarks/REPAIR_PROTOCOL.md).

# T4 E2B NF4 repair development pilot v1

This is a separate experiment from REPAIR_PROTOCOL.md (31B QAT). No GPU result has been measured yet.

- Base weights: google/gemma-4-E2B-it at a recorded immutable revision.
- Quantization: bitsandbytes NF4 with double quantization and FP16 compute. This is NOT the official W4A16 QAT checkpoint.
- Backend: Transformers, one local GPU, eager attention, no vLLM, no BF16, no paid endpoint.
- Same 23 public dev tasks and gold-free paired contexts as the existing preparation pipeline.
- Same system instructions and same issue prefix in both arms; issue prefix capped at 1,536 tokens.
- Total prompt cap: 4,096 tokens. Trim only the context further when needed; record truncation.
- Greedy decoding, seed 0, thinking disabled, at most 1,024 generated tokens.
- One completed attempt per task/arm; alternate order; checkpoint every attempt. Resume skips existing attempts, including errors. Changed settings/model/input manifests cannot resume into the same directory.
- Keep errors, invalid/empty diffs, truncated outputs and raw responses. No automatic quality-based retries or model substitution.
- Primary outcome requires separate SWE-bench Docker test reports; generation statuses are not successful repairs.
- Treat these as E2B NF4 development results only. Do not merge with 31B QAT results or infer official competition compatibility/eligibility.
- Record installed packages, CUDA/GPU details, model revision/config hash, request hashes and input checksum. PyTorch allocation/reservation readings are process observations, not total device memory.
- Real T4 fit and speed require a runtime test. Free Colab sessions can disconnect; save outputs before leaving.

# T4 E2B NF4 structured-edit development protocol v2

This development experiment follows the analyzed v1 run. It is not a new holdout.
Freeze this protocol and implementation commit before observing v2 model output.

## Fixed conditions

- Same 23 public SWE-bench Lite dev tasks, exact base commits and gold-free contexts as v1.
- Base model google/gemma-4-E2B-it at 4adf15748de9e1a0097b6274cee9c15836c41c37.
- NF4 double quantization, FP16, eager attention, greedy decoding, seed zero.
- 4,096 input tokens; shared 1,536-token issue prefix; 1,024 output tokens per generation.
- Alternate arm order by sorted task index. Separate v2 output directory and model label.

## Changed intervention

The model emits one JSON object with at most eight exact replacements.
Each needs an existing Python source path, nonempty old text that occurs exactly once,
and different new text. Replacements refer to the original source; overlaps, net no-ops,
unsafe paths and test edits are rejected. Empty edits are an abstention.
Python renders sorted unified diffs, including missing-final-newline markers.

The validator loads UTF-8 Python text from the exact source archive whose hash was
recorded in the input bundle. It never loads reference patches or executes target code.
The full snapshot is available only to validation, not added to model context.
Per-task snapshot hashes are recorded and checked before each attempt.

Allow one correction after an edit-validation error or output-cap failure. Both arms
use identical retry rules. Feedback includes the validation error and previous response,
capped at 1,200 tokens; it competes with source context inside the same input cap.
Save both responses, validation errors, prompt hashes, truncation, tokens, latency and
peak allocator/reservation readings. Runtime errors stop the task without retry.
Resume skips every saved outcome; never select the best of repeated runs.

## Evaluation

Report all 23 planned tasks per arm, failures and abstentions included. Separate initial
acceptance, retry acceptance, source-changing application and test-resolved outcomes.
Sum generation tokens/time over both steps and report retry counts; v2 has a larger
maximum generation budget than v1. Do not attribute cross-version differences solely
to graph retrieval or output format.

Run ordinary git apply --check against pinned snapshots, then controlled test grading
with reference-fix and unchanged-program controls. Record environment overrides and
incomplete grading. No applicable-patch count is a repair-success count.

The CPU smoke test deliberately inserts a comment into a real pre-fix file. It checks
the renderer/application contract and is not model performance evidence.

## Next independent evaluation

The committed repair-holdout-v1.json selects 12 public test tasks: three per repository
from Django, Matplotlib, scikit-learn and SymPy. These repositories are absent from the
analyzed dev set. Selection uses the lowest SHA256(salt + instance_id), without looking
at issue content, reference patches or model outputs. Dataset shard hashes and base
commits are pinned. Use the same finalized v2 policy, at most 48 generations total
(12 tasks x two arms x two attempts). Do not tune or filter after observing outcomes.
Public-data pretraining contamination is possible. No holdout model result exists yet.

# Gemma repair pilot v1

Frozen before Gemma predictions. Status: GPU inference and grading have not run.

- Population: all 23 SWE-bench Lite dev tasks, revision 6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2. Already used for retrieval analysis; this is a development pilot.
- Model: google/gemma-4-31B-it-qat-w4a16-ct. Record declared immutable model revision and hashes of local weights/config/tokenizer files.
- One completion per task per arm. No best-of selection, retries or overwriting earlier outputs.
- Temperature 0, top_p 1, seed 0; thinking disabled; 4,096 output tokens; 300-second timeout.
- Same system instructions and issue. Only context differs.
- BM25: ten seeds, no expansion. Graph: five seeds, one hop. Both: 8,000 characters, ten results, 30 visited nodes, 20 neighbors.
- Alternate arm order by task index. Server handles one sequence at a time.
- Gold-free inputs contain issue text, pre-fix context, IDs and provenance only. No hints, patches, test patches or expected outcomes.
- Generated patches are not executed in the inference process.
- Preserve raw responses, finish reasons, usage, invalid/empty patches and errors.
- Grade using the official SWE-bench harness on a separate Docker-capable host, dev split, different run IDs for the two arms.
- Before model comparison, validate gold-patch and genuinely unfixed-source controls. An empty-prediction skip is not an unfixed-source test control.
- Primary: paired resolved-task rate over all 23 planned tasks. Missing test reports cannot count as repairs or silently disappear.
- No claim of repair improvement without actual test reports.

This is a one-shot context-to-patch pilot, not the official multi-turn ADK competition agent. Mock integration checks test plumbing only, never Gemma performance.

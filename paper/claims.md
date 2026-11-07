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

Do not submit this working paper as a completed empirical study. The strongest next milestone is an audited real-world retrieval experiment; a larger corpus is useful only if its provenance and evaluation quality are credible.

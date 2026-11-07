# Research review and positioning

Reviewed 2026-11-07. This is a working evidence ledger, not a completed systematic review.

## Prior work

| Source | Established contribution | Implication for LocalCodeGraph |
| --- | --- | --- |
| [CodexGraph](https://arxiv.org/abs/2408.03910), [NAACL paper](https://aclanthology.org/2025.naacl-long.7/) | Repository graphs exposed through graph queries for agent navigation; multiple repository-level benchmarks. | Cite as foundational work. A graph interface alone is not our novelty. The earlier claim that code was merely forthcoming is outdated; the paper links an application demo. |
| [RepoGraph](https://github.com/ozyyshr/RepoGraph), [paper](https://arxiv.org/abs/2410.14684) | Repository-level context module integrated with SWE-agent and Agentless. | Compare end-to-end repair under matched budgets, not just fewer reads. |
| [LocAgent](https://github.com/gersteinlab/LocAgent), [paper](https://arxiv.org/abs/2503.09089) | Lightweight heterogeneous dependency graphs, graph-guided localization, and Loc-Bench. | Closest localization baseline. Avoid claiming lightweight graph navigation as new. Current README also links reusable CodeNib indexes; inspect this integration before claiming a new reusable-index contribution. |

## Public competition work inspected

[happyc0der/gemma-swe-agent](https://github.com/happyc0der/gemma-swe-agent) publishes an extensive experiment log. Its author reports repeated calls, malformed tool arguments, context/budget failures, and differences between proxy and faithful evaluation. These are author-reported observations, not independently reproduced results. We take bounded traversal and faithful model/harness evaluation as design requirements.

[velocitylabo/gemma4-agent-budget-audit](https://github.com/velocitylabo/gemma4-agent-budget-audit) publishes a preregistered fixed-budget verify/retry comparison. Its README reports 17 versus 17 resolves on 43 qualifying held-out problems for its primary comparison. This supports using paired outcomes and reporting negative results; it does not establish that verification never helps.

The [paper-track notebook listing](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/code?competitionId=163111&excludeNonAccessedDatasources=true) exposes titles including GraphNav-Gemma, CRAG, TRACE, graph slicing and AST-compression projects. We have seen listings, not their complete implementations or verified results. They must not be described as reviewed baselines yet. The Writeups page did not expose readable submissions through the available browser tool.

## Proposed contribution, still to validate

A reusable offline retrieval resource with:
1. Explicit context and traversal budgets.
2. Structural/lexical/dense ablations and deterministic provenance.
3. Snapshot freshness checks and lexical fallback for missing semantic retrieval.
4. Reproducible resource measurements and a failure-oriented evaluation suite.

SQLite and memory mapping are engineering choices, not novel algorithms. The case for a resource award must come from demonstrated utility, usable interfaces, documentation, reproducibility and trustworthy benchmarks.

## Claims ledger

| Claim from initial concept | Status |
| --- | --- |
| 35–60% fewer tool calls | Unmeasured hypothesis; do not report as a result. |
| Full agent fits 16–24 GB | Unverified. Measure weights, KV cache, runtime overhead, CPU RSS and index separately. |
| 80 additional repositories | Planned, not collected. Start with a smaller licensed, audited set. |
| Multi-language tree-sitter parsing | Not implemented; current extractor is Python AST. |
| Official graph ingestion | Normalized JSON importer exists; raw competition adapter pending actual schema inspection. |
| Guaranteed harness compatibility | Not established; standalone Python APIs cannot automatically be registered as competition tools. |

## Source precedence

Official competition pages and the exact downloaded harness version govern integration. Community copies can help understand behavior but may be stale. Freeze dataset checksums, harness wheel versions, model revision, prompts and configs for every experiment. Competition deadlines/model allowances should be checked again before submission.

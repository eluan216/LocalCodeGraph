# Structured-edit T4 pilot v2 and post-hoc revalidation

## Scope and provenance

I completed the paired 23-task public-development experiment with the same E2B
base-model revision and input bundle as v1. All 46 original attempt records,
manifest and prediction exports are preserved under original/. Each attempt
used both allowed generations, for 92 generations total. Model revision:
4adf15748de9e1a0097b6274cee9c15836c41c37; original toolkit commit:
48fa23825b2a1cfbb124a086673ae97fe1aad02d. This is NF4/FP16 E2B on a T4,
not a 31B or official W4A16 QAT result.

The input checksum is
ff3898c557d6bb97d6e1539047db3b61f4001e1aa81e84efe91cab856da759f4.
The SWE-bench Lite public dev revision is
6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2.
The dataset, source-archive and per-task snapshot fingerprints are recorded in
the original manifest. Raw environment dumps and private transfer URLs are omitted.

## Original outcome

Both arms produced zero accepted patches under the original strict-JSON protocol.
There were 45 final JSON-format errors and one output-limit error. The original
prediction exports contain all 23 planned tasks per arm with empty patches.

The schema example used package/file.py. A supplied response copied that example
path and an issue reproducer instead of editing repository source. Many responses
wrapped JSON in a Markdown code fence, which the original parser rejected before
source validation. The first and second responses were byte-for-byte identical
for 22 BM25 tasks and 20 graph tasks, making these retries largely unproductive.

| Recorded generation metric | BM25 | Graph |
| --- | ---: | ---: |
| Tasks / generations | 23 / 46 | 23 / 46 |
| Original accepted patches | 0 | 0 |
| Generation output tokens, both steps | 7,624 | 6,083 |
| Recorded generation seconds, both steps | 824.84 | 684.97 |
| Maximum PyTorch reserved GiB | 7.80 | 7.93 |
| Maximum PyTorch allocated GiB | 7.53 | 7.65 |

Allocator readings do not measure total device memory. Time excludes preparation
and loading, and different output lengths prevent a controlled speedup claim.
V2 allows twice as many generations as v1.

## Post-hoc rule

After observing the formatting failure, I introduced a separately labeled CPU
interpretation: permit exactly one complete JSON fence with no outside prose,
while retaining all path, exact-text, duplicate-key, overlap, no-op, test-exclusion
and ordinary Git application checks. Runtime failures and original output limits
remain errors. Every saved step is examined, but only the final step is exported;
an earlier valid response is never selected over a failed final retry.

This changes interpretation of saved outputs, not the original v2 outcome.
It does not regenerate responses or use reference fixes during validation.

| Final-step post-hoc outcome | BM25 | Graph |
| --- | ---: | ---: |
| Applicable source-changing patch | 2 | 0 |
| Empty-edits abstention | 7 | 6 |
| Validation or original generation error | 14 | 17 |

The only candidates are pydicom-1694 and sqlfluff-2419, both BM25. The first moves
data-element access inside an existing exception handler; the second adds trailing
whitespace to a list-opening line. Applicability alone establishes neither repair
correctness nor a graph retrieval benefit.

## Controlled test verification

I graded both independently reproduced candidates with SWE-bench 4.1.0 in Docker.
Both reference-fix controls resolved their task; both unchanged-program controls
failed the labeled bug test. The controls applied successfully and covered every
benchmark-labeled test.

| Task and condition | Bug tests passing | Labeled regression tests passing | Resolved |
| --- | ---: | ---: | --- |
| pydicom-1694 reference | 1/1 | 26/26 | Yes |
| pydicom-1694 unfixed | 0/1 | 26/26 | No |
| pydicom-1694 BM25 post-hoc | 1/1 | 26/26 | Yes |
| sqlfluff-2419 reference | 1/1 | None provided | Yes |
| sqlfluff-2419 unfixed | 0/1 | None provided | No |
| sqlfluff-2419 BM25 post-hoc | 0/1 | None provided | No |

The pydicom candidate passes
test_suppress_invalid_tags_with_failed_dataelement and all 26 labeled regression
tests (27 tests in the selected test file). It moves self[key] inside the try
block so failures during data-element access can be handled by the existing
suppress_invalid_tags behavior. The SQLFluff candidate changes only trailing
whitespace and still fails the diagnostic-description assertion. That task has
no labeled PASS_TO_PASS regression tests; none are claimed.

Pydicom ran on Python 3.10.22 / pytest 7.4.4 with the disclosed compatibility pin.
SQLFluff ran on Python 3.9.25 / pytest 8.4.2 using its official spec unchanged.
No reference code or test labels were altered.

This establishes **one test-verified BM25 repair after post-hoc normalization**.
The original v2 run still exported zero patches. It is not a complete official
23-task harness score, a graph improvement, a 31B result or an independent holdout
result. Only the two applicable candidates were test-graded.

[Successful reproduction and controlled grading run](https://github.com/eluan216/LocalCodeGraph/actions/runs/42483558413).
Machine-readable outcomes: [post-hoc revalidation](posthoc-report.json) and
[test controls](controlled-grading.json). Original attempt records remain unchanged.


## Reproduction

Regenerate gold-free inputs and snapshots from their pinned revisions and verify
all original checksums. Run benchmarks/revalidate_structured_run.py with a separate
output directory. The [reproduction and grading workflow](../../.github/workflows/evaluate-v2-posthoc.yml)
freezes the two-candidate set and stops candidate grading if test controls fail.

The test harness is SWE-bench 4.1.0 in Docker. Pydicom uses the same documented
pytest 7.4.4 compatibility pin for reference fix, unfixed control and candidate.
SQLFluff initially uses its official dependency spec unchanged. Environment
failures are not counted as model repair failures.

## Interpretation

This small, already analyzed public-development set supports diagnosis and
development, not general superiority or a competition score. Post-hoc formatting
tolerance recovers two BM25 candidates but no graph candidate. The next prompt
describes the schema without a sample path and asks for paths and old text from
pre-fix source headers. V3 and the reserved holdout have no model results here.

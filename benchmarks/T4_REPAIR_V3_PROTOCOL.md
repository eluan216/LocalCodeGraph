# V3 grounded structured edits and v2 post-hoc revalidation

The user-reported v2 run ended with 23 errors per arm. Final errors were 45 JSON
format errors and one output limit. One supplied response copied the prompt's
illustrative path and issue reproducer. This diagnosis has not audited every raw
response, so no other latent source-validation outcomes are known.

Post-hoc rule: accept bare JSON or one complete unlabeled/json fence with no
outside prose; preserve duplicate-key and all source-validation checks. Preserve
original attempts and manifest hashes, record every step, export only the final
saved step, reject original output limits and runtime failures, and run ordinary
Git application checks. This is a new CPU interpretation of old outputs, not a
changed original outcome, new generation run or official repair score.

V3 uses GROUNDED_SYSTEM, which describes the field schema without an example
path. It instructs the model to copy paths from pre-fix source headers and old
text from that source, and abstain if unsupported. The remaining model revision,
input/issue/output caps, greedy decoding and two-generation maximum match v2.
The v3 runner and output directory are separate. Code/validator fingerprints
prevent mixing changed runs. Evaluate on development tasks before finalizing
the holdout policy. No V3 inference or repair gains are claimed.

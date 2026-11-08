"""Post-hoc CPU revalidation; does not regenerate, select best attempts or edit a run."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from localcodegraph.repair_t4 import load_records
from localcodegraph.structured_edits import EditError, load_snapshot, parse_edits, render_edits

def apply_check(response, patch, sources):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name in {e["path"] for e in parse_edits(response, allow_fence=True)}:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(sources[name].encode("utf-8"))
        candidate = root / "candidate.diff"
        candidate.write_bytes(patch.encode("utf-8"))
        subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
        result = subprocess.run(["git", "-C", str(root), "apply", "--check", str(candidate)],
                                capture_output=True, text=True)
        if result.returncode:
            raise EditError("git apply check failed: " + result.stderr.strip())

def revalidate(run_dir, source_dir, output_dir, inputs=None, manifest=None):
    run = Path(run_dir).resolve()
    output = Path(output_dir).resolve()
    if output == run or run in output.parents:
        raise ValueError("post-hoc output must be outside the original run directory")
    inputs = Path(inputs) if inputs else run / "gold-free-inputs/inputs.jsonl"
    manifest = Path(manifest) if manifest else run / "gold-free-inputs/manifest.json"
    records, input_manifest = load_records(inputs, manifest)
    config = json.loads((run / "manifest.json").read_bytes())
    if config["inputs_manifest"] != input_manifest:
        raise ValueError("input manifest differs from original run")
    output.mkdir(parents=True, exist_ok=False)
    report = {"protocol":"posthoc-single-json-fence-v1",
        "scope":"Revalidation only; no generation or test-based repair score. Final saved step only for exports.",
        "original_manifest_sha256":hashlib.sha256((run / "manifest.json").read_bytes()).hexdigest(),
        "planned_per_arm":len(records), "arms":{}, "records":[]}
    for arm in ("bm25", "graph"):
        counts = Counter()
        predictions = []
        for record in records:
            path = run / "attempts" / (record["instance_id"] + "." + arm + ".json")
            row = {"instance_id":record["instance_id"], "arm":arm, "steps":[]}
            patch = ""
            if not path.exists():
                row["final_status"] = "missing"
            else:
                raw = path.read_bytes()
                event = json.loads(raw)
                if event["instance_id"] != record["instance_id"] or event["arm"] != arm:
                    raise ValueError("attempt identity differs")
                row.update(original_attempt_sha256=hashlib.sha256(raw).hexdigest(),
                           original_status=event["status"], original_error=event.get("error"))
                sources, digest = load_snapshot(source_dir, record)
                if digest != config["snapshot_sha256"][record["instance_id"]]:
                    raise ValueError("snapshot differs from original run")
                if event.get("source_snapshot_sha256", digest) != digest:
                    raise ValueError("attempt snapshot differs")
                for index, step in enumerate(event.get("steps", [])):
                    outcome = {"index":index, "original_error":step.get("validation_error")}
                    candidate = ""
                    try:
                        if step.get("runtime_error"):
                            raise EditError("original runtime error: " + step["runtime_error"])
                        if step.get("output_limit"):
                            raise EditError("original output hit generation limit")
                        candidate = render_edits(step.get("response", ""), sources, allow_fence=True)
                        if candidate:
                            apply_check(step["response"], candidate, sources)
                        outcome["status"] = "applicable" if candidate else "abstain"
                    except EditError as error:
                        candidate = ""
                        outcome.update(status="error", error=str(error))
                    row["steps"].append(outcome)
                    # Always overwrite: never select an earlier candidate over the final step.
                    patch = candidate
                row["final_status"] = row["steps"][-1]["status"] if row["steps"] else "no_saved_generation"
                if row["steps"] and row["steps"][-1].get("error"):
                    counts["error: " + row["steps"][-1]["error"]] += 1
            counts[row["final_status"]] += 1
            report["records"].append(row)
            predictions.append({"instance_id":record["instance_id"],
                "model_name_or_path":"gemma-E2B-NF4-v2-posthoc-fence-final-step",
                "model_patch":patch})
        report["arms"][arm] = dict(counts)
        (output / f"predictions.{arm}.posthoc.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in predictions), encoding="utf-8")
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--inputs")
    parser.add_argument("--manifest")
    args = parser.parse_args()
    report = revalidate(args.run_dir, args.source_dir, args.output_dir, args.inputs, args.manifest)
    print(json.dumps({"scope":report["scope"], "arms":report["arms"]}, indent=2))
    print("Full diagnostics saved to", Path(args.output_dir) / "report.json")

if __name__ == "__main__":
    main()

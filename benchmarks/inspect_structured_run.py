"""Audit v2 exports without executing target code or loading gold patches."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from localcodegraph.repair_t4 import load_records
from localcodegraph.structured_edits import load_snapshot, render_edits, parse_edits

def audit(output, inputs, manifest, source_dir):
    output = Path(output)
    records, input_manifest = load_records(inputs, manifest)
    config = json.loads((output / "manifest.json").read_text())
    if config["inputs_manifest"] != input_manifest:
        raise ValueError("run/input manifests differ")
    report = {"study":config["settings"]["study"], "planned_per_arm":len(records),
              "scope":"CPU generation/application audit, not test-based repair grading", "arms":{}}
    for arm in ("bm25", "graph"):
        counts = Counter(planned=len(records))
        totals = Counter()
        events = []
        for record in records:
            path = output / "attempts" / (record["instance_id"] + "." + arm + ".json")
            if not path.exists():
                counts["missing"] += 1
                continue
            event = json.loads(path.read_text())
            counts["completed"] += 1
            counts[event["status"]] += 1
            steps = event.get("steps", [])
            counts["retries"] += max(0, len(steps) - 1)
            counts["first_generation_accepted"] += int(bool(steps) and "validation_error" not in steps[0]
                                                      and "runtime_error" not in steps[0])
            totals["output_tokens"] += sum(s.get("output_tokens", 0) for s in steps)
            totals["input_tokens"] += sum(s.get("input_tokens", 0) for s in steps)
            totals["generation_seconds"] += sum(s.get("seconds", 0) for s in steps)
            if event["patch"]:
                sources, digest = load_snapshot(source_dir, record)
                if digest != config["snapshot_sha256"][record["instance_id"]]:
                    raise ValueError("snapshot checksum differs")
                allow_fence = config["settings"].get("edit_format") == "exact-replacement-json-fence-v2"
                reproduced = render_edits(steps[-1]["response"], sources, allow_fence=allow_fence)
                if reproduced != event["patch"]:
                    raise ValueError("exported patch does not match accepted response")
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    edits = parse_edits(steps[-1]["response"], allow_fence=allow_fence)
                    for name in {e["path"] for e in edits}:
                        target = root / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(sources[name].encode())
                    patch = root / "candidate.diff"
                    patch.write_bytes(reproduced.encode())
                    subprocess.run(["git","init","-q",str(root)],check=True)
                    checked = subprocess.run(["git","-C",str(root),"apply","--check",str(patch)],
                                              capture_output=True,text=True)
                    counts["git_apply_pass"] += int(checked.returncode == 0)
                    events.append({"instance_id":record["instance_id"],
                                   "git_apply":checked.returncode == 0, "diagnostic":checked.stderr})
                    if checked.returncode:
                        raise ValueError("deterministic patch failed git apply: " + checked.stderr)
        exported = [json.loads(line) for line in (output / f"predictions.{arm}.jsonl").read_text().splitlines()]
        expected = {}
        for record in records:
            path = output / "attempts" / (record["instance_id"] + "." + arm + ".json")
            if path.exists():
                expected[record["instance_id"]] = json.loads(path.read_text())["patch"]
        if len(exported) != len(expected) or {r["instance_id"]:r["model_patch"] for r in exported} != expected:
            raise ValueError("prediction exports differ from checkpoints")
        report["arms"][arm] = {"counts":dict(counts), "totals":dict(totals), "application":events}
    return report

def main():
    parser = argparse.ArgumentParser()
    for name in ("output-dir", "inputs", "manifest", "source-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    report = audit(args.output_dir, args.inputs, args.manifest, args.source_dir)
    (Path(args.output_dir) / "cpu-audit.json").write_text(json.dumps(report,indent=2) + "\n")
    print(json.dumps(report,indent=2))

if __name__ == "__main__":
    main()

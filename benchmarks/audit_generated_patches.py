"""Check original exported patches against pre-fix source. Does not run project code."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from run_swebench_lite import obtain_tasks, obtain_source

def git(root, *args):
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args],
                          capture_output=True, text=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    inputs = Path(args.input_dir)
    predictions = {}
    for arm in ("bm25", "graph"):
        rows = [json.loads(line) for line in (inputs / f"predictions.{arm}.jsonl").read_text().splitlines()]
        if len(rows) != 23 or len({r["instance_id"] for r in rows}) != 23:
            raise ValueError("each arm requires exactly 23 unique task IDs")
        predictions[arm] = {r["instance_id"]: r for r in rows}
    summary = json.loads((inputs / "generation-summary.json").read_text())
    records = []
    with tempfile.TemporaryDirectory() as temporary:
        tasks, dataset = obtain_tasks(Path(temporary),
            summary["model"]["inputs_manifest"]["dataset"]["revision"])
        if any(set(predictions[arm]) != {t["instance_id"] for t in tasks} for arm in predictions):
            raise ValueError("prediction tasks differ from the pinned dataset")
        for task in tasks:
            nonempty = [arm for arm in predictions if predictions[arm][task["instance_id"]]["model_patch"]]
            if not nonempty:
                continue
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source, archive_sha = obtain_source(task, root)
                for command in (("init",), ("add", ".")):
                    result = git(source, *command)
                    if result.returncode:
                        raise RuntimeError(result.stderr)
                committed = git(source, "-c", "user.name=LocalCodeGraph Audit",
                                "-c", "user.email=audit@local.invalid", "commit", "-qm", "pre-fix snapshot")
                if committed.returncode:
                    raise RuntimeError(committed.stderr)
                for arm in nonempty:
                    patch = predictions[arm][task["instance_id"]]["model_patch"]
                    patch_file = root / "candidate.diff"
                    patch_file.write_text(patch)
                    checked = git(source, "apply", "--check", str(patch_file))
                    row = {"id": task["instance_id"], "arm": arm, "repo": task["repo"],
                           "base_commit": task["base_commit"], "archive_sha256": archive_sha,
                           "strict_git_apply_check": checked.returncode == 0,
                           "diagnostic": checked.stderr.strip()}
                    if checked.returncode == 0:
                        applied = git(source, "apply", str(patch_file))
                        row["applied"] = applied.returncode == 0
                        if applied.returncode == 0:
                            row["changes_worktree"] = git(source, "diff", "--quiet").returncode == 1
                            row["changed_files"] = git(source, "diff", "--name-only").stdout.splitlines()
                            git(source, "reset", "--hard", "HEAD")
                    records.append(row)
    report = {"dataset": dataset, "scope": "Strict patch application only; no test execution or repair score.",
              "records": records, "arms": {}}
    for arm in predictions:
        rows = [r for r in records if r["arm"] == arm]
        report["arms"][arm] = {"planned": 23, "nonempty_exports": len(rows),
            "strict_apply_pass": sum(r["strict_git_apply_check"] for r in rows),
            "worktree_changes": sum(r.get("changes_worktree", False) for r in rows)}
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("LCG_AUDIT_JSON=" + json.dumps(report), flush=True)

if __name__ == "__main__":
    main()

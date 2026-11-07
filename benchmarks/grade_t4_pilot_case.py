"""Official test-based grading of the only strict-applicable, source-changing export."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from run_swebench_lite import obtain_tasks

INSTANCE = "pydicom__pydicom-1413"
MARKER_PATCH = (
    "diff --git a/.lcg_unfixed_control b/.lcg_unfixed_control\n"
    "new file mode 100644\n--- /dev/null\n+++ b/.lcg_unfixed_control\n"
    "@@ -0,0 +1 @@\n+Unmodified program-source control.\n"
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        tasks, dataset = obtain_tasks(Path(directory), "6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2")
    task = next(t for t in tasks if t["instance_id"] == INSTANCE)
    (output / "task.json").write_text(json.dumps([task]))
    rows = [json.loads(line) for line in (Path(args.input_dir) / "predictions.graph.jsonl").read_text().splitlines()]
    candidate = next(r["model_patch"] for r in rows if r["instance_id"] == INSTANCE)
    cases = {"gold": task["patch"], "unfixed": MARKER_PATCH, "graph": candidate}
    statuses = {}
    for label, patch in cases.items():
        model_name = "lcg-control-" + label
        prediction = output / f"{label}.jsonl"
        prediction.write_text(json.dumps({"instance_id": INSTANCE,
            "model_name_or_path": model_name, "model_patch": patch}) + "\n")
        run_id = "lcg-pydicom1413-" + label + "-" + os.environ.get("GITHUB_RUN_ID", "local")
        command = [sys.executable, "-m", "swebench.harness.run_evaluation",
            "--dataset_name", str(output / "task.json"), "--split", "dev",
            "--predictions_path", str(prediction), "--instance_ids", INSTANCE,
            "--max_workers", "1", "--namespace", "none",
            "--cache_level", "instance", "--timeout", "600", "--run_id", run_id]
        print("Grading", label, "with swebench 4.1.0", flush=True)
        log_path = output / f"{label}.log"
        try:
            with log_path.open("w") as log:
                process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                         text=True, timeout=1500)
            matches = [p for p in Path("logs").rglob("report.json")
                       if run_id in str(p) and INSTANCE in str(p)]
            report = matches[0] if len(matches) == 1 else output / "missing-report.json"
            test_log = report.parent / "test_output.txt"
            statuses[label] = {"exit_code": process.returncode,
                              "report": json.loads(report.read_text()) if report.exists() else None,
                              "test_output_head": test_log.read_text()[:10000] if test_log.exists() else None,
                              "test_output_tail": test_log.read_text()[-10000:] if test_log.exists() else None,
                              "log_tail": log_path.read_text()[-4000:]}
        except Exception as error:
            statuses[label] = {"error": str(error)}
        (output / "status.json").write_text(json.dumps(statuses, indent=2))
        case_report = statuses[label].get("report") or {}
        resolved = case_report.get(INSTANCE, {}).get("resolved")
        if (label == "gold" and resolved is not True) or (label == "unfixed" and resolved is not False):
            print("Control validation failed; stopping before model grading.", flush=True)
            break
    result = {"instance_id": INSTANCE, "dataset": dataset, "harness": "swebench==4.1.0",
              "scope": "Single-case controlled grading, not a complete 23-task repair score",
              "cases": statuses}
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print("LCG_GRADE_JSON=" + json.dumps(result), flush=True)

if __name__ == "__main__":
    main()

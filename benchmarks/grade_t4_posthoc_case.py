"""Official test-based grading of the only strict-applicable, source-changing export."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from run_swebench_lite import obtain_tasks

INSTANCE = None
MARKER_PATCH = (
    "diff --git a/.lcg_unfixed_control b/.lcg_unfixed_control\n"
    "new file mode 100644\n--- /dev/null\n+++ b/.lcg_unfixed_control\n"
    "@@ -0,0 +1 @@\n+Unmodified program-source control.\n"
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--instance", required=True)
    args = parser.parse_args()
    global INSTANCE
    INSTANCE = args.instance
    if INSTANCE not in {"pydicom__pydicom-1694", "sqlfluff__sqlfluff-2419"}:
        raise ValueError("instance is outside the frozen post-hoc candidate set")
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        tasks, dataset = obtain_tasks(Path(directory), "6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2")
    task = next(t for t in tasks if t["instance_id"] == INSTANCE)
    (output / "task.json").write_text(json.dumps([task]))
    rows = [json.loads(line) for line in (Path(args.input_dir) / "predictions.bm25.posthoc.jsonl").read_text().splitlines()]
    candidate = next(r["model_patch"] for r in rows if r["instance_id"] == INSTANCE)
    cases = {"gold": task["patch"], "unfixed": MARKER_PATCH, "bm25_posthoc": candidate}
    # This pre-fix project uses nose-style setup/teardown, removed in pytest 8.
    # Pin only the test dependency; do not change project code, labels or patches.
    wrapper = (
        "from swebench.harness.constants.python import SPECS_PYDICOM\n"
        "import runpy\n"
        "for spec in SPECS_PYDICOM.values():\n"
        "    spec['pip_packages'] = ['pytest==7.4.4' if p == 'pytest' else p "
        "for p in spec.get('pip_packages', [])]\n"
        "runpy.run_module('swebench.harness.run_evaluation', run_name='__main__')\n"
    )
    statuses = {}
    for label, patch in cases.items():
        model_name = "lcg-control-" + label
        prediction = output / f"{label}.jsonl"
        prediction.write_text(json.dumps({"instance_id": INSTANCE,
            "model_name_or_path": model_name, "model_patch": patch}) + "\n")
        run_id = "lcg-v2-" + INSTANCE + "-" + label + "-" + os.environ.get("GITHUB_RUN_ID", "local")
        command = [sys.executable, "-c", wrapper,
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
                              "test_failure_excerpt": (test_log.read_text()[max(0, test_log.read_text().find("FAILURES")):][:12000]
                                  if test_log.exists() else None),
                              "test_output_head": test_log.read_text()[:10000] if test_log.exists() else None,
                              "test_output_tail": test_log.read_text()[-10000:] if test_log.exists() else None,
                              "log_tail": log_path.read_text()[-4000:]}
        except Exception as error:
            statuses[label] = {"error": str(error)}
        (output / "status.json").write_text(json.dumps(statuses, indent=2))
        case_report = statuses[label].get("report") or {}
        resolved = case_report.get(INSTANCE, {}).get("resolved")
        detail = case_report.get(INSTANCE, {})
        status = detail.get("tests_status", {})
        f2p = status.get("FAIL_TO_PASS", {})
        p2p = status.get("PASS_TO_PASS", {})
        expected_f2p = task["FAIL_TO_PASS"]
        expected_p2p = task["PASS_TO_PASS"]
        if isinstance(expected_f2p, str):
            expected_f2p = json.loads(expected_f2p)
        if isinstance(expected_p2p, str):
            expected_p2p = json.loads(expected_p2p)
        observed_f2p = set(f2p.get("success", []) + f2p.get("failure", []))
        observed_p2p = set(p2p.get("success", []) + p2p.get("failure", []))
        complete = (detail.get("patch_successfully_applied") is True
            and observed_f2p == set(expected_f2p) and observed_p2p == set(expected_p2p))
        qualified = complete and not p2p.get("failure") and (
            (resolved is True and not f2p.get("failure")) if label == "gold"
            else (resolved is False and bool(f2p.get("failure"))) if label == "unfixed" else True)
        statuses[label]["control_qualified"] = qualified if label in {"gold", "unfixed"} else None
        (output / "status.json").write_text(json.dumps(statuses, indent=2))
        if label in {"gold", "unfixed"} and not qualified:
            print("Control validation failed; stopping before model grading.", flush=True)
            break
    result = {"instance_id": INSTANCE, "dataset": dataset, "harness": "swebench==4.1.0",
              "environment_override": {"pydicom_pytest": "7.4.4",
                  "reason": "Restore legacy nose-style setup/teardown support; applied to pydicom specs only"},
              "scope": "Controlled grading of a post-hoc final-step candidate, not a complete official repair score",
              "cases": statuses}
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print("LCG_GRADE_JSON=" + json.dumps(result), flush=True)

if __name__ == "__main__":
    main()

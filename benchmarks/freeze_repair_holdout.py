"""Freeze test task IDs without inspecting reference patches or model outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from run_swebench_lite import download, DATASET
REVISION = "6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2"
REPOS = ("django/django", "matplotlib/matplotlib", "scikit-learn/scikit-learn", "sympy/sympy")
SALT = "localcodegraph-repair-holdout-v1"

def test_rows(directory, revision=REVISION):
    import pyarrow.parquet as pq
    metadata = directory / "test-metadata.json"
    download(f"https://huggingface.co/api/datasets/{DATASET}/revision/{revision}", metadata)
    names = sorted(s["rfilename"] for s in json.loads(metadata.read_text())["siblings"]
                   if s["rfilename"].startswith("data/test-") and s["rfilename"].endswith(".parquet"))
    if not names:
        raise ValueError("no test parquet files")
    rows, files = [], []
    for index, name in enumerate(names):
        path = directory / f"test-{index}.parquet"
        download(f"https://huggingface.co/datasets/{DATASET}/resolve/{revision}/{name}", path)
        files.append({"path":name, "sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
        rows.extend(pq.read_table(path).to_pylist())
    return rows, {"dataset":DATASET, "revision":revision, "split":"test", "files":files}

def freeze(rows, dataset):
    selected = []
    for repo in REPOS:
        candidates = [r for r in rows if r["repo"] == repo]
        candidates.sort(key=lambda r: hashlib.sha256((SALT + r["instance_id"]).encode()).hexdigest())
        if len(candidates) < 3:
            raise ValueError("not enough tasks for fixed repository quota")
        for row in candidates[:3]:
            selected.append({key: row[key] for key in ("instance_id", "repo", "base_commit")})
    return {"study":"t4-e2b-nf4-holdout-v1", "dataset":dataset,
            "selection":{"salt":SALT, "per_repository":3, "repositories":list(REPOS),
                         "rule":"lowest SHA256(salt + instance_id), no filtering on issue, patch or model output"},
            "tasks":sorted(selected, key=lambda r:r["instance_id"])}

def obtain_frozen_tasks(directory, path):
    frozen = json.loads(Path(path).read_text())
    rows, dataset = test_rows(directory, frozen["dataset"]["revision"])
    if freeze(rows, dataset) != frozen:
        raise ValueError("holdout manifest differs from frozen selection")
    by_id = {r["instance_id"]:r for r in rows}
    return [by_id[t["instance_id"]] for t in frozen["tasks"]], dict(dataset, holdout=frozen)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        rows, dataset = test_rows(Path(directory))
        frozen = freeze(rows, dataset)
    Path(args.output).write_text(json.dumps(frozen, indent=2) + "\n")
    print("LCG_HOLDOUT_JSON=" + json.dumps(frozen), flush=True)

if __name__ == "__main__":
    main()

"""Materialize hash-verified pre-fix Python text for offline edit validation."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from run_swebench_lite import obtain_source
from localcodegraph.repair_t4 import load_records

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    records, _ = load_records(args.inputs, args.manifest)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    checksums = {}
    for record in records:
        target = output / (record["instance_id"] + ".json")
        if not target.exists():
            with tempfile.TemporaryDirectory() as directory:
                source, digest = obtain_source(record, Path(directory))
                if digest != record["source_archive_sha256"]:
                    raise ValueError("source archive hash differs from original inputs")
                files = {}
                for path in sorted(source.rglob("*.py")):
                    try:
                        files[path.relative_to(source).as_posix()] = path.read_bytes().decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                value = {key: record[key] for key in ("repo", "base_commit", "source_archive_sha256")}
                value["files"] = files
                temporary = target.with_suffix(".tmp")
                temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
                temporary.replace(target)
        from localcodegraph.structured_edits import load_snapshot
        _, checksums[record["instance_id"]] = load_snapshot(output, record)
        print("Verified source", record["instance_id"], flush=True)
    (output / "manifest.json").write_text(json.dumps(checksums, indent=2) + "\n")

if __name__ == "__main__":
    main()

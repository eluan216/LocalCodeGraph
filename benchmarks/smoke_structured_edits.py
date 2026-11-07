"""Synthetic edit against real pre-fix source; CPU applicability, not repair scoring."""
import json
from pathlib import Path
import subprocess
import tempfile
from run_swebench_lite import obtain_source
from localcodegraph.structured_edits import render_edits

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    source, digest = obtain_source({"repo":"pydicom/pydicom",
        "base_commit":"f909c76e31f759246cec3708dadd173c5d6e84b1"}, root)
    path = "pydicom/util/codify.py"
    original = (source / path).read_bytes().decode("utf-8")
    old = original.splitlines(keepends=True)[0]
    response = json.dumps({"edits":[{"path":path, "old":old,
                                    "new":"# LocalCodeGraph synthetic application smoke\n" + old}]})
    patch = render_edits(response, {path:original})
    candidate = root / "candidate.diff"
    candidate.write_bytes(patch.encode())
    subprocess.run(["git", "init", "-q", str(source)], check=True)
    subprocess.run(["git", "-C", str(source), "apply", "--check", str(candidate)], check=True)
    subprocess.run(["git", "-C", str(source), "apply", str(candidate)], check=True)
    assert (source / path).read_bytes().decode() == "# LocalCodeGraph synthetic application smoke\n" + original
    print("REAL_SOURCE_EDIT_SMOKE=" + json.dumps({"repo":"pydicom/pydicom",
        "base_commit":"f909c76e31f759246cec3708dadd173c5d6e84b1",
        "archive_sha256":digest, "git_apply":True, "scope":"synthetic edit only, not model repair"}))

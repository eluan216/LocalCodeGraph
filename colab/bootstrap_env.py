"""Create a notebook venv without requiring apt, sudo or system ensurepip."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

BOOTSTRAP_URL = "https://bootstrap.pypa.io/virtualenv.pyz"

def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        print("Command failed:", command, flush=True)
        print(result.stdout, flush=True)
        print(result.stderr, flush=True)
    return result

def bootstrap(destination, force_bootstrap=False):
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    python = destination / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    print("Base interpreter:", sys.executable, sys.version, flush=True)
    method, bootstrap_sha = "stdlib-venv", None
    ready = False
    if not force_bootstrap:
        created = run([sys.executable, "-m", "venv", "--system-site-packages", str(destination)])
        if created.returncode == 0 and python.exists():
            ready = run([str(python), "-m", "pip", "--version"]).returncode == 0
    if not ready:
        print("Using PyPA virtualenv bootstrap; system ensurepip is not required.", flush=True)
        archive = destination.parent / "lcg-virtualenv.pyz"
        try:
            with urllib.request.urlopen(BOOTSTRAP_URL, timeout=120) as response:
                data = response.read()
        except Exception as error:
            raise RuntimeError("Could not download the PyPA virtualenv bootstrap: " + str(error)) from error
        bootstrap_sha = hashlib.sha256(data).hexdigest()
        archive.write_bytes(data)
        created = run([sys.executable, str(archive), "--system-site-packages",
                       "--no-download", str(destination)])
        if created.returncode:
            raise RuntimeError("PyPA virtualenv also failed; its complete output is printed above.")
        method = "pypa-virtualenv-pyz"
    checked = run([str(python), "-m", "pip", "--version"])
    if checked.returncode:
        raise RuntimeError("Environment was created but pip is unavailable; see output above.")
    print(checked.stdout, flush=True)
    metadata = {"method": method, "base_python": sys.executable, "python_version": sys.version,
                "bootstrap_url": BOOTSTRAP_URL if bootstrap_sha else None,
                "bootstrap_sha256": bootstrap_sha, "pip": checked.stdout.strip()}
    (destination / "lcg-bootstrap.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return str(python)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True)
    parser.add_argument("--force-bootstrap", action="store_true",
                        help="Exercise the ensurepip-independent fallback directly")
    args = parser.parse_args()
    print("Environment Python:", bootstrap(args.destination, args.force_bootstrap))

if __name__ == "__main__":
    main()

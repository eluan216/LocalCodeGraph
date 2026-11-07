import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import io

path = Path(__file__).resolve().parents[1] / "colab/bootstrap_env.py"
spec = importlib.util.spec_from_file_location("colab_bootstrap", path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

class BootstrapTests(unittest.TestCase):
    def test_failed_venv_falls_back_without_ensurepip(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "env"
            target.mkdir()  # Simulate the partial directory left by failed venv.
            outcomes = [subprocess.CompletedProcess([], 1, "", "ensurepip unavailable"),
                        subprocess.CompletedProcess([], 0, "created", ""),
                        subprocess.CompletedProcess([], 0, "pip seeded", "")]
            with patch.object(helper, "run", side_effect=outcomes) as commands:
                with patch.object(helper.urllib.request, "urlopen", return_value=io.BytesIO(b"test-bootstrap")):
                    helper.bootstrap(target)
            self.assertIn("--system-site-packages", commands.call_args_list[1].args[0])
            self.assertNotIn("ensurepip", commands.call_args_list[1].args[0])
            self.assertTrue((target / "lcg-bootstrap.json").exists())

    def test_download_failure_explains_cause(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(helper.urllib.request, "urlopen", side_effect=OSError("offline")):
                with self.assertRaisesRegex(RuntimeError, "Could not download"):
                    helper.bootstrap(Path(directory) / "env", force_bootstrap=True)

if __name__ == "__main__":
    unittest.main()

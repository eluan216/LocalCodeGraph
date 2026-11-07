"""CPU checks for T4 preparation/checkpoints. No GPU/model result is simulated."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from localcodegraph.repair_t4 import fit_prompt, load_records, save_attempt, export_predictions, prepare_output, load_t4_model
from unittest.mock import Mock

def record():
    return {"instance_id": "owner__repo-1", "repo": "owner/repo",
            "base_commit": "a" * 40, "problem_statement": "issue",
            "source_archive_sha256": "b" * 64,
            "contexts": {arm: {"text": "x" * 8000, "characters": 8000, "selected": []}
                         for arm in ("bm25", "graph")}}

class CharacterTokenizer:
    def encode(self, text, add_special_tokens=False):
        return list(map(ord, text))
    def decode(self, ids, skip_special_tokens=True):
        return "".join(map(chr, ids))
    def apply_chat_template(self, messages, **kwargs):
        assert kwargs["enable_thinking"] is False
        return "\n".join(message["content"] for message in messages) + "\nASSISTANT:"

class T4Tests(unittest.TestCase):
    def test_prompt_cap_and_common_issue_prefix(self):
        value = record()
        value["problem_statement"] = "i" * 2000
        texts = []
        for arm in ("bm25", "graph"):
            text, info = fit_prompt(CharacterTokenizer(), value, arm)
            self.assertLessEqual(info["input_tokens"], 4096)
            self.assertTrue(info["issue_truncated"])
            self.assertTrue(info["context_truncated"])
            texts.append(text.split("PRE-FIX SOURCE CONTEXT:")[0])
        self.assertEqual(texts[0], texts[1])

    def test_checkpoint_exports_keep_model_label_and_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "attempts").mkdir()
            save_attempt(output, {"instance_id": "owner__repo-1", "arm": "bm25",
                                  "status": "error", "patch": "", "error": "out of memory"})
            result = export_predictions(output, [record()])
            self.assertEqual(sum(result.values()), 1)
            prediction = json.loads((output / "predictions.bm25.jsonl").read_text())
            self.assertIn("E2B", prediction["model_name_or_path"])
            self.assertNotIn("31B", prediction["model_name_or_path"])
            self.assertEqual(prediction["model_patch"], "")
            self.assertEqual((output / "predictions.graph.jsonl").read_text(), "")
            self.assertFalse(list((output / "attempts").glob("*.tmp")))

    def test_inputs_are_checksum_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = (json.dumps(record()) + "\n").encode()
            (root / "inputs.jsonl").write_bytes(raw)
            metadata = {"tasks": 1, "inputs_sha256": hashlib.sha256(raw).hexdigest()}
            (root / "manifest.json").write_text(json.dumps(metadata))
            rows, _ = load_records(root / "inputs.jsonl", root / "manifest.json")
            self.assertEqual(len(rows), 1)
            (root / "inputs.jsonl").write_bytes(raw + b" ")
            with self.assertRaises(ValueError):
                load_records(root / "inputs.jsonl", root / "manifest.json")

    def test_loader_does_not_force_unsupported_audio_sdpa(self):
        loader = Mock()
        load_t4_model(loader, "local-model", "quantization", "float16")
        kwargs = loader.from_pretrained.call_args.kwargs
        self.assertEqual(kwargs["attn_implementation"], "eager")

    def test_startup_manifest_can_be_corrected_without_deleting_history(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            old = {"settings": {"attention": "sdpa"}, "tasks": ["example"]}
            new = {"settings": {"attention": "eager"}, "tasks": ["example"]}
            prepare_output(output, old, resume=False)
            prepare_output(output, new, resume=True)
            self.assertEqual(json.loads((output / "manifest.json").read_text()), new)
            backups = list(output.glob("manifest.sdpa-startup.*.json"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(json.loads(backups[0].read_text()), old)

    def test_manifest_correction_refuses_existing_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            old = {"settings": {"attention": "sdpa"}}
            new = {"settings": {"attention": "eager"}}
            prepare_output(output, old, resume=False)
            attempt = output / "attempts" / "completed.json"
            attempt.write_text("preserve")
            with self.assertRaises(ValueError):
                prepare_output(output, new, resume=True)
            self.assertEqual(attempt.read_text(), "preserve")
            self.assertEqual(json.loads((output / "manifest.json").read_text()), old)

    def test_both_notebooks_compile_without_saved_outputs(self):
        root = Path(__file__).resolve().parents[1] / "colab"
        for path in root.glob("*.ipynb"):
            notebook = json.loads(path.read_text())
            for index, cell in enumerate(notebook["cells"]):
                if cell["cell_type"] == "code":
                    compile("".join(cell["source"]), f"{path.name}:{index}", "exec")
                    self.assertEqual(cell["outputs"], [])

if __name__ == "__main__":
    unittest.main()

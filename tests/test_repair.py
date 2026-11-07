"""CPU/mock checks only: none of these tests run Gemma inference."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from localcodegraph.repair import MODEL, extract_patch, generate, payload, validate_record, request_json

DIFF = "--- a/code.py\n+++ b/code.py\n@@ -1 +1 @@\n-old\n+new\n"

def record():
    return {"instance_id": "owner__repo-1", "repo": "owner/repo",
            "base_commit": "a" * 40, "problem_statement": "Repair behavior",
            "source_archive_sha256": "b" * 64,
            "contexts": {arm: {"text": arm, "selected": [], "characters": len(arm)}
                         for arm in ("bm25", "graph")}}

class RepairTests(unittest.TestCase):
    def test_gold_fields_rejected(self):
        value = record()
        value["patch"] = DIFF
        with self.assertRaises(ValueError):
            validate_record(value)

    def test_parameters_match_between_arms(self):
        left, right = payload(record(), "bm25"), payload(record(), "graph")
        self.assertEqual({k: v for k, v in left.items() if k != "messages"},
                         {k: v for k, v in right.items() if k != "messages"})
        self.assertEqual(left["messages"][0], right["messages"][0])
        self.assertEqual(left["max_tokens"], 4096)

    def test_patch_parser_rejects_prose_paths_and_tests(self):
        self.assertEqual(extract_patch(DIFF), DIFF)
        self.assertEqual(extract_patch(""), "")
        for value in ["Explanation\n" + DIFF,
                      DIFF.replace("code.py", "../escape.py"),
                      DIFF.replace("code.py", "tests/test_code.py")]:
            with self.assertRaises(ValueError):
                extract_patch(value)

    def test_remote_endpoint_rejected_before_network(self):
        with self.assertRaises(ValueError):
            request_json("https://example.com/v1", "/models")

    def test_mock_generation_exports_both_arms_and_preserves_errors(self):
        def mock_server(base, route, body=None):
            if route == "/models":
                return {"data": [{"id": MODEL}]}
            if body["messages"][-1]["content"].endswith("graph"):
                return {"choices": [{"finish_reason": "length",
                                     "message": {"content": DIFF}}]}
            return {"choices": [{"finish_reason": "stop",
                                 "message": {"content": DIFF}}], "usage": {"completion_tokens": 10}}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "mock-output"
            with patch("localcodegraph.repair.request_json", side_effect=mock_server):
                generate([record()], "http://127.0.0.1:8000/v1", output, {"test_only": True})
            bm25 = json.loads((output / "predictions.bm25.jsonl").read_text())
            graph = json.loads((output / "predictions.graph.jsonl").read_text())
            self.assertEqual(bm25["model_patch"], DIFF)
            self.assertEqual(graph["model_patch"], "")
            events = [json.loads(line) for line in (output / "traces.jsonl").read_text().splitlines()]
            self.assertEqual([e["status"] for e in events], ["patch", "error"])

    def test_preparation_allow_list_omits_gold(self):
        if sys.platform != "linux":
            self.skipTest("preparation imports the Linux evaluation helper")
        location = Path(__file__).resolve().parents[1] / "benchmarks"
        sys.path.insert(0, str(location))
        try:
            spec = importlib.util.spec_from_file_location("prepare_repair_inputs",
                                                         location / "prepare_repair_inputs.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            task = {"instance_id": "owner__repo-1", "repo": "owner/repo",
                    "base_commit": "a" * 40, "problem_statement": "issue",
                    "patch": "GOLD", "test_patch": "SECRET", "hints_text": "HINT"}
            result = module.sanitized_record(task, record()["contexts"], "b" * 64)
            self.assertEqual(set(result), set(record()))
            self.assertNotIn("GOLD", json.dumps(result))
            self.assertNotIn("SECRET", json.dumps(result))
        finally:
            sys.path.remove(str(location))

    def test_colab_notebook_cells_compile_and_have_no_outputs(self):
        path = Path(__file__).resolve().parents[1] / "colab" / "LocalCodeGraph_Gemma_Repair.ipynb"
        notebook = json.loads(path.read_text())
        self.assertEqual(notebook["nbformat"], 4)
        for number, cell in enumerate(notebook["cells"]):
            self.assertIn("id", cell)
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), f"cell-{number}", "exec")
                self.assertEqual(cell["outputs"], [])

if __name__ == "__main__":
    unittest.main()

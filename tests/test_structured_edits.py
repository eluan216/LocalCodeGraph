"""CPU contract tests: exact edits, retry accounting and actual git applicability."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from localcodegraph.structured_edits import EditError, render_edits, validated_generation, load_snapshot
from localcodegraph.repair_t4_v2 import fit_prompt, SETTINGS
from test_repair_t4 import CharacterTokenizer, record

def response(path="pkg/a.py", old="return 1", new="return 2"):
    return json.dumps({"edits": [{"path": path, "old": old, "new": new}]})

class EditTests(unittest.TestCase):
    def test_rendered_diff_applies_and_changes_exact_source(self):
        for source in ("def f():\n    return 1\n", "def f():\n    return 1",
                       "def f():\r\n    return 1\r\n"):
            with self.subTest(source=repr(source)), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "pkg").mkdir()
                path = root / "pkg/a.py"
                path.write_bytes(source.encode())
                patch = render_edits(response(), {"pkg/a.py": source})
                candidate = root / "edit.diff"
                candidate.write_bytes(patch.encode())
                subprocess.run(["git", "init", "-q", str(root)], check=True)
                subprocess.run(["git", "-C", str(root), "apply", "--check", str(candidate)], check=True)
                subprocess.run(["git", "-C", str(root), "apply", str(candidate)], check=True)
                self.assertEqual(path.read_bytes(), source.replace("return 1", "return 2").encode())

    def test_rejects_invalid_edits(self):
        sources = {"pkg/a.py": "return 1\nreturn 1\n"}
        invalid = [
            response(old="missing"), response(), response(old="", new="x"),
            response(old="return 1", new="return 1"), response(path="../a.py"),
            response(path="/a.py"), response(path="pkg\\a.py"), response(path="pkg/./a.py"),
            response(path="missing.py"), response(path="tests/a.py"),
            response(path="pkg/test_a.py"), response(path="pkg/a_test.py"),
            response(path="pkg/conftest.py"), '{"edits":[],"edits":[]}',
            '{"edits":[],"extra":1}', 'explanation {"edits":[]}',
            '{"edits":[{"path":"pkg/a.py","old":1,"new":"x"}]}',
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(EditError):
                render_edits(value, sources)

    def test_original_source_matching_and_overlap(self):
        sources = {"pkg/a.py": "abcdef\n"}
        value = {"edits": [
            {"path": "pkg/a.py", "old": "abc", "new": "ABC"},
            {"path": "pkg/a.py", "old": "def", "new": "DEF"}]}
        self.assertIn("+ABCDEF", render_edits(json.dumps(value), sources))
        value["edits"][1]["old"] = "bcde"
        with self.assertRaises(EditError):
            render_edits(json.dumps(value), sources)
        with self.assertRaises(EditError):
            render_edits(response(old="aa"), {"pkg/a.py": "aaa"})

    def test_empty_abstention_and_noop(self):
        self.assertEqual(render_edits('{"edits":[]}', {}), "")
        value = {"edits":[{"path":"a.py","old":"a","new":"ab"},
                          {"path":"a.py","old":"b","new":""}]}
        # Two swaps may leave the file identical, despite individually changing edits.
        with self.assertRaises(EditError):
            render_edits(json.dumps(value), {"a.py": "ab"})
    
    def test_retry_is_bounded_and_retains_validation_errors(self):
        calls = []
        def generate(feedback):
            calls.append(feedback)
            return {"response": "bad" if len(calls) == 1 else response()}
        result = validated_generation(generate, lambda r: render_edits(r, {"pkg/a.py":"return 1\n"}))
        self.assertEqual(result["status"], "patch")
        self.assertEqual(len(result["steps"]), 2)
        self.assertIn("Previous response failed", calls[1])
        self.assertIn("validation_error", result["steps"][0])
        result = validated_generation(lambda f: {"response":"bad"}, lambda r: render_edits(r, {}))
        self.assertEqual(result["status"], "error")
        self.assertEqual(len(result["steps"]), 2)

    def test_runtime_errors_are_not_retried_or_allowed_to_erase_first_step(self):
        count = 0
        def generate(feedback):
            nonlocal count
            count += 1
            if count == 2:
                raise RuntimeError("GPU failure")
            return {"response":"bad"}
        result = validated_generation(generate, lambda r: render_edits(r, {}))
        self.assertEqual(count, 2)
        self.assertIn("validation_error", result["steps"][0])
        self.assertEqual(result["steps"][1]["runtime_error"], "GPU failure")

    def test_snapshot_provenance_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            value = record()
            snapshot = {key:value[key] for key in ("repo","base_commit","source_archive_sha256")}
            snapshot["files"] = {"pkg/a.py":"return 1"}
            path = Path(directory) / (value["instance_id"] + ".json")
            path.write_text(json.dumps(snapshot))
            files, digest = load_snapshot(directory, value)
            self.assertEqual(files, snapshot["files"])
            self.assertEqual(len(digest), 64)
            snapshot["base_commit"] = "c" * 40
            path.write_text(json.dumps(snapshot))
            with self.assertRaises(ValueError):
                load_snapshot(directory, value)

    def test_checkpoint_export_audit_checks_patch_against_saved_response(self):
        import hashlib
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
        from inspect_structured_run import audit
        from localcodegraph.repair_t4_v2 import export_predictions, save_attempt
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = record()
            raw = (json.dumps(value) + "\n").encode()
            (root / "inputs.jsonl").write_bytes(raw)
            metadata = {"tasks":1, "inputs_sha256":hashlib.sha256(raw).hexdigest()}
            (root / "inputs-manifest.json").write_text(json.dumps(metadata))
            snapshots = root / "sources"
            snapshots.mkdir()
            snapshot = {key:value[key] for key in ("repo","base_commit","source_archive_sha256")}
            snapshot["files"] = {"pkg/a.py":"return 1\n"}
            (snapshots / (value["instance_id"] + ".json")).write_text(json.dumps(snapshot))
            _, digest = load_snapshot(snapshots, value)
            output = root / "run"
            (output / "attempts").mkdir(parents=True)
            (output / "manifest.json").write_text(json.dumps({"settings":SETTINGS,
                "inputs_manifest":metadata, "snapshot_sha256":{value["instance_id"]:digest}}))
            event = {"instance_id":value["instance_id"], "arm":"bm25", "status":"patch",
                "patch":render_edits(response(), snapshot["files"]),
                "steps":[{"response":response(), "output_tokens":10, "input_tokens":20, "seconds":1.0}]}
            save_attempt(output, event)
            export_predictions(output, [value])
            result = audit(output, root / "inputs.jsonl", root / "inputs-manifest.json", snapshots)
            self.assertEqual(result["arms"]["bm25"]["counts"]["git_apply_pass"], 1)
            self.assertEqual(result["arms"]["graph"]["counts"]["missing"], 1)
            event["patch"] += "corruption"
            save_attempt(output, event)
            with self.assertRaises(ValueError):
                audit(output, root / "inputs.jsonl", root / "inputs-manifest.json", snapshots)
            from revalidate_structured_run import revalidate
            fence = chr(96) * 3
            event.update(status="error", patch="", steps=[
                {"response":fence + "json\n" + response() + "\n" + fence},
                {"response":fence + "json\n" + response(path="package/file.py") + "\n" + fence}])
            save_attempt(output, event)
            original = (output / "attempts" / (value["instance_id"] + ".bm25.json")).read_bytes()
            posthoc = root / "posthoc"
            result = revalidate(output, snapshots, posthoc, root / "inputs.jsonl",
                                root / "inputs-manifest.json")
            self.assertEqual(result["records"][0]["steps"][0]["status"], "applicable")
            self.assertEqual(result["records"][0]["final_status"], "error")
            self.assertEqual(json.loads((posthoc / "predictions.bm25.posthoc.jsonl").read_text())["model_patch"], "")
            self.assertEqual((output / "attempts" / (value["instance_id"] + ".bm25.json")).read_bytes(), original)
            event["steps"] = event["steps"][:1]
            save_attempt(output, event)
            result = revalidate(output, snapshots, root / "posthoc-valid", root / "inputs.jsonl",
                                root / "inputs-manifest.json")
            self.assertEqual(result["arms"]["bm25"]["applicable"], 1)
            with self.assertRaises(ValueError):
                revalidate(output, snapshots, output / "nested", root / "inputs.jsonl",
                           root / "inputs-manifest.json")

    def test_single_json_fence_is_explicit_and_fail_closed(self):
        from localcodegraph.structured_edits import parse_edits
        fence = chr(96) * 3
        body = response()
        sources = {"pkg/a.py":"return 1\n"}
        for wrapper in (fence + "json\n" + body + "\n" + fence,
                        fence + "\n" + body + "\n" + fence,
                        " \n" + fence + "json\r\n" + body + "\r\n" + fence + "\n "):
            with self.subTest(wrapper=wrapper):
                self.assertEqual(render_edits(wrapper, sources, allow_fence=True),
                                 render_edits(body, sources))
                with self.assertRaises(EditError):
                    render_edits(wrapper, sources)
        for bad in ("prose\n" + fence + "json\n" + body + "\n" + fence,
                    fence + "json\n" + body + "\n" + fence + "\nprose",
                    fence + "json\n" + body,
                    fence + "json\n" + body + "\n" + fence + "\n" + fence + "json\n{}\n" + fence):
            with self.subTest(bad=bad), self.assertRaises(EditError):
                parse_edits(bad, allow_fence=True)

    def test_fence_does_not_bypass_fabricated_path_or_source_checks(self):
        fence = chr(96) * 3
        for value in (response(path="package/file.py"), response(old="fabricated example")):
            with self.subTest(value=value), self.assertRaises(EditError):
                render_edits(fence + "json\n" + value + "\n" + fence,
                             {"pkg/a.py":"return 1\n"}, allow_fence=True)

    def test_grounded_prompt_does_not_contain_example_path(self):
        from localcodegraph.structured_edits import GROUNDED_SYSTEM
        self.assertNotIn("package/file.py", GROUNDED_SYSTEM)
        self.assertIn("PRE-FIX SOURCE CONTEXT", GROUNDED_SYSTEM)
        self.assertIn("Copy path from a source header", GROUNDED_SYSTEM)

    def test_output_limit_cannot_be_accepted(self):
        result = validated_generation(lambda f: {"response": '{"edits":[]}', "output_limit":True},
                                      lambda r: render_edits(r, {}))
        self.assertEqual(result["status"], "error")

    def test_retry_prompt_has_same_cap_and_common_issue(self):
        value = record()
        value["problem_statement"] = "i" * 2000
        texts = []
        for arm in ("bm25", "graph"):
            text, info = fit_prompt(CharacterTokenizer(), value, arm, "feedback " * 2000)
            self.assertLessEqual(info["input_tokens"], 4096)
            self.assertIn("VALIDATION FEEDBACK", text)
            texts.append(text.split("PRE-FIX SOURCE CONTEXT:")[0])
        self.assertEqual(texts[0], texts[1])
        self.assertIn("v2", SETTINGS["study"])

if __name__ == "__main__":
    unittest.main()

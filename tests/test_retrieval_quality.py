"""Behavioral regressions and analytical cases; these are not a research benchmark."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from localcodegraph import GraphStore
from localcodegraph.retrieval import context_for_task
from localcodegraph.evaluation import compare, evaluate

def node(identifier, text, start=1, end=1, kind="Function", name=None):
    return {"id": identifier, "kind": kind, "path": identifier + ".py",
            "name": name or identifier, "text": text, "start_line": start, "end_line": end}

class QualityTests(unittest.TestCase):
    def test_identifier_boundaries(self):
        with GraphStore(":memory:") as store:
            store.replace([node("a", "pass", name="decodeInput"),
                           node("b", "pass", name="HTTPResponseParser"),
                           node("c", "pass", name="load_config")], [])
            self.assertEqual(store.search("decode input")[0]["id"], "a")
            self.assertEqual(store.search("response parser")[0]["id"], "b")
            self.assertEqual(store.search("load config")[0]["id"], "c")

    def test_module_does_not_repeat_function(self):
        body = "def decode():\n    return 1"
        function = node("f", body, start=2, end=3, name="decode")
        module = node("m", "# header\n" + body, start=1, end=3, kind="Module")
        function["path"] = module["path"] = "a.py"
        with GraphStore(":memory:") as store:
            store.replace([function, module], [{"source": "m", "target": "f", "type": "contains"}])
            result = context_for_task(store, "decode")
            self.assertEqual(result["context"].count("def decode()"), 1)
            self.assertTrue(any(s["reason"] == "overlapping_source" for s in result["skipped"]))

    def test_call_neighbor_beats_containment_hub(self):
        with GraphStore(":memory:") as store:
            store.replace([node("entry", "decode"), node("helper", "secret"),
                           node("hub", "unrelated")],
                          [{"source": "hub", "target": "entry", "type": "contains"},
                           {"source": "entry", "target": "helper", "type": "calls"}])
            result = context_for_task(store, "decode", seed_k=1, max_results=2)
            self.assertEqual([n["id"] for n in result["selected"]], ["entry", "helper"])

    def test_stale_source_cannot_enter_context(self):
        with tempfile.TemporaryDirectory() as directory, GraphStore(":memory:") as store:
            path = Path(directory) / "entry.py"
            path.write_bytes(b"old")
            item = node("entry", "decode")
            item["sha256"] = hashlib.sha256(b"old").hexdigest()
            store.replace([item], [])
            self.assertTrue(context_for_task(store, "decode", root=directory)["selected"])
            path.write_bytes(b"changed")
            result = context_for_task(store, "decode", root=directory)
            self.assertEqual(result["context"], "")
            self.assertEqual(result["skipped"][0]["reason"], "stale_or_unverifiable")

    def test_budget_and_result_cap_apply_to_both_arms(self):
        with GraphStore(":memory:") as store:
            store.replace([node("entry", "decode"), node("helper", "secret")],
                          [{"source": "entry", "target": "helper", "type": "calls"}])
            tasks = [{"id": "t", "query": "decode", "relevant_nodes": ["helper"]}]
            report = compare(store, tasks, k=2, max_chars=1000, bootstrap_samples=100)
            self.assertEqual(report["wins"], ["t"])
            self.assertEqual(report["paired_mean_recall_delta"], 1)
            for arm in ("baseline", "candidate"):
                row = report[arm]["records"][0]
                self.assertLessEqual(len(row["predicted"]), 2)
                self.assertLessEqual(row["characters"], 1000)
            self.assertEqual(evaluate(store, tasks, k=0)["mean_recall_at_k"], 0)

    def test_comparison_reports_graph_regression(self):
        # A lexical target can be excluded when graph spends its reserved slot
        # on a misleading dependency. Preserve this loss instead of hiding it.
        with GraphStore(":memory:") as store:
            store.replace([node("a", "decode"), node("b", "decode extra extra extra extra"),
                           node("c", "irrelevant")],
                          [{"source": "a", "target": "c", "type": "calls"}])
            tasks = [{"id": "loss", "query": "decode", "relevant_nodes": ["b"]}]
            report = compare(store, tasks, k=2, bootstrap_samples=100)
            self.assertEqual(report["losses"], ["loss"])
            self.assertEqual(report["paired_mean_recall_delta"], -1)

if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from localcodegraph import GraphStore
from localcodegraph.indexer import index_python
from localcodegraph.retrieval import context_for_task, reciprocal_rank_fusion
from localcodegraph.evaluation import evaluate

def node(identifier, text="", path="example.py"):
    return {"id": identifier, "kind": "Function", "path": path, "name": identifier,
            "text": text, "start_line": 1, "end_line": 1}

class GraphTests(unittest.TestCase):
    def setUp(self):
        self.store = GraphStore(":memory:")
        self.store.replace([node("parse", "decode input"), node("helper", "validate"),
                            node("other", "unrelated")],
                           [{"source": "parse", "target": "helper", "type": "calls"}])
    def tearDown(self):
        self.store.close()

    def test_import_failure_preserves_previous_graph(self):
        with self.assertRaises(ValueError):
            self.store.replace([node("new")],
                               [{"source": "new", "target": "missing", "type": "calls"}])
        self.assertIsNotNone(self.store.node("parse"))

    def test_failed_sql_transaction_preserves_previous_graph(self):
        invalid = node("new")
        invalid["kind"] = None
        with self.assertRaises(Exception):
            self.store.replace([invalid], [])
        self.assertIsNotNone(self.store.node("parse"))
        self.assertEqual(len(self.store.search("decode")), 1)

    def test_induced_subgraph_and_incoming_neighbors(self):
        self.assertEqual(len(self.store.get_code_subgraph(["parse"])["edges"]), 0)
        self.assertEqual(len(self.store.get_code_subgraph(["parse", "helper"])["edges"]), 1)
        self.assertEqual(self.store.get_code_neighbors("helper")[0]["source"], "parse")
        self.assertEqual(self.store.get_code_neighbors("parse", "imports"), [])

    def test_literal_search_and_invalid_limits(self):
        self.assertEqual(self.store.search('decode " OR *')[0]["id"], "parse")
        self.assertEqual(self.store.search(""), [])
        self.assertEqual(self.store.get_code_neighbors("parse", max_neighbors=0), [])
        with self.assertRaises(ValueError):
            self.store.search("decode", -1)

    def test_context_budget_and_expansion(self):
        result = context_for_task(self.store, "decode", seed_k=1, max_nodes=3)
        self.assertEqual([item["id"] for item in result["selected"]], ["parse", "helper"])
        bounded = context_for_task(self.store, "decode", max_chars=20)
        self.assertLessEqual(len(bounded["context"]), 20)
        self.assertEqual(bounded["characters"], len(bounded["context"]))

    def test_fusion_deduplicates_each_ranking(self):
        result = reciprocal_rank_fusion([{"id": "a"}, {"id": "a"}], [{"id": "b"}])
        self.assertEqual(result[0]["score"], result[1]["score"])

    def test_path_traversal_rejected(self):
        for path in ["../secret.py", "/etc/passwd", "C:/secret.py"]:
            with self.assertRaises(ValueError):
                self.store.replace([node("escape", path=path)], [])

    def test_evaluation_known_answer_and_unknown_gold(self):
        result = evaluate(self.store, [{"id": "t", "query": "decode",
                                       "relevant_nodes": ["parse"]}])
        self.assertEqual(result["mrr"], 1)
        with self.assertRaises(ValueError):
            evaluate(self.store, [{"id": "t", "query": "decode",
                                  "relevant_nodes": ["absent"]}])

class IndexerTests(unittest.TestCase):
    def test_index_source_spans_calls_and_freshness(self):
        with tempfile.TemporaryDirectory() as directory, GraphStore(":memory:") as store:
            path = Path(directory) / "sample.py"
            path.write_text("def helper():\n    return 1\n\ndef caller():\n    return helper()\n",
                            encoding="utf-8")
            index_python(directory, store)
            caller = "sample.py::caller@4"
            helper = "sample.py::helper@1"
            graph = store.get_code_subgraph([caller, helper])
            self.assertEqual(graph["edges"], [{"source": caller, "target": helper, "type": "calls"}])
            self.assertTrue(store.is_fresh(caller, directory))
            path.write_text("# changed\n", encoding="utf-8")
            self.assertFalse(store.is_fresh(caller, directory))

    def test_syntax_errors_recorded_and_nested_definitions_found(self):
        with tempfile.TemporaryDirectory() as directory, GraphStore(":memory:") as store:
            (Path(directory) / "bad.py").write_text("def ???", encoding="utf-8")
            (Path(directory) / "valid.py").write_text(
                "try:\n    pass\nexcept Exception:\n    def fallback():\n        pass\n",
                encoding="utf-8")
            result = index_python(directory, store)
            self.assertEqual(result["skipped"][0]["reason"], "SyntaxError")
            self.assertIsNotNone(store.node("valid.py::fallback@4"))

if __name__ == "__main__":
    unittest.main()

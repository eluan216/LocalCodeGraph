import importlib.util
from pathlib import Path
import unittest
import sys
if sys.platform != 'linux':
    raise unittest.SkipTest('Linux-only benchmark resource API')
from localcodegraph import GraphStore

spec = importlib.util.spec_from_file_location("real_benchmark",
    Path(__file__).resolve().parents[1] / "benchmarks" / "run_swebench_lite.py")
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)

class RealEvaluationTests(unittest.TestCase):
    def test_file_metrics_deduplicate_and_preserve_rank(self):
        value = benchmark.metrics(["a.py", "a.py", "b.py"], {"b.py", "c.py"})
        self.assertEqual(value["recall"], 0.5)
        self.assertEqual(value["mrr"], 0.5)
        self.assertEqual(value["hit"], 1)

    def test_empty_symbol_labels_are_not_zero_accuracy(self):
        self.assertIsNone(benchmark.metrics(["a"], set())["recall"])

    def test_reference_labels_use_old_source_paths_for_renames(self):
        try:
            import unidiff
        except ImportError:
            self.skipTest("benchmark-only dependency not installed")
        patch = "--- a/old.py\n+++ b/new.py\n@@ -1,2 +1,2 @@\n def f():\n-    return 1\n+    return 2\n"
        with GraphStore(":memory:") as store:
            store.replace([{"id": "f", "kind": "Function", "path": "old.py", "name": "f",
                            "start_line": 1, "end_line": 2, "text": "def f():\n    return 1"}], [])
            files, symbols = benchmark.reference_labels(patch, store)
            self.assertEqual(files, {"old.py"})
            self.assertEqual(symbols, {"f"})

    def test_cluster_interval_preserves_zero_difference(self):
        self.assertEqual(benchmark.interval([0, 0, 0], ["a", "a", "b"]), [0, 0])

    def test_failed_task_stays_in_primary_denominator(self):
        success = {"repo": "a", "predictions": {}}
        for arm in ("bm25", "graph"):
            success["predictions"][arm] = {
                "file_metrics": {"recall": 1, "hit": 1, "mrr": 1},
                "characters": 10, "median_retrieval_seconds": 0.1,
                "symbol_metrics": {"recall": None}}
        report = benchmark.summarize([success, {"repo": "b", "error": "download"}])
        self.assertFalse(report["complete"])
        self.assertEqual(report["arms"]["bm25"]["mean_file_recall"], 0.5)
        self.assertEqual(report["tasks"], 2)

if __name__ == "__main__":
    unittest.main()

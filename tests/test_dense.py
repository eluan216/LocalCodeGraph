import json
import tempfile
import unittest
from pathlib import Path
try:
    import numpy as np
except ImportError:
    np = None

@unittest.skipIf(np is None, "optional numpy dependency not installed")
class DenseTests(unittest.TestCase):
    def test_chunked_search_matches_cosine_order_and_excludes_zero(self):
        from localcodegraph.dense import DenseIndex
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            np.save(root / "vectors.npy", np.array([[1, 0], [0, 1], [1, 1], [0, 0]], dtype="float32"))
            (root / "ids.json").write_text(json.dumps(["a", "b", "c", "zero"]))
            index = DenseIndex(root / "vectors.npy", root / "ids.json")
            hits = index.search_vector([1, 0], k=4, chunk_size=1)
            self.assertEqual([hit["id"] for hit in hits], ["a", "c", "b"])
            with self.assertRaises(ValueError):
                index.search_vector([0, 0])
            with self.assertRaises(ValueError):
                index.search_vector([1, 0, 0])
            # Release the mmap before TemporaryDirectory cleanup on Windows.
            index.vectors._mmap.close()

if __name__ == "__main__":
    unittest.main()

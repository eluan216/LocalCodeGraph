"""Optional CPU dense search. Supply vectors from the same encoder as the index."""
import json
import numpy as np
from .store import limit

class DenseIndex:
    def __init__(self, vectors_path, ids_path):
        self.vectors = np.load(vectors_path, mmap_mode="r", allow_pickle=False)
        with open(ids_path, encoding="utf-8") as stream:
            self.ids = json.load(stream)
        if self.vectors.ndim != 2 or self.vectors.shape[1] == 0:
            raise ValueError("vectors must be a nonempty-width matrix")
        if not np.issubdtype(self.vectors.dtype, np.floating):
            raise ValueError("vectors must use a floating dtype")
        if not isinstance(self.ids, list) or len(self.ids) != self.vectors.shape[0]:
            raise ValueError("one node ID is required per vector")
        if any(not isinstance(i, str) for i in self.ids) or len(set(self.ids)) != len(self.ids):
            raise ValueError("node IDs must be unique strings")

    def search_vector(self, query_vector, k=10, chunk_size=4096):
        limit(k)
        limit(chunk_size, 1_000_000)
        if chunk_size == 0:
            raise ValueError("chunk_size must be positive")
        query = np.asarray(query_vector, dtype=np.float32)
        if query.shape != (self.vectors.shape[1],) or not np.isfinite(query).all():
            raise ValueError("query dimensions or values are invalid")
        norm = np.linalg.norm(query)
        if norm == 0:
            raise ValueError("query must have nonzero norm")
        query = query / norm
        if not k:
            return []
        best = []
        for start in range(0, len(self.ids), chunk_size):
            block = np.asarray(self.vectors[start:start + chunk_size], dtype=np.float32)
            if not np.isfinite(block).all():
                raise ValueError("index contains nonfinite vectors")
            norms = np.linalg.norm(block, axis=1)
            scores = (block @ query) / np.where(norms > 0, norms, 1)
            candidates = [(self.ids[start + offset], float(score))
                          for offset, score in enumerate(scores) if norms[offset] > 0]
            best = sorted(best + candidates, key=lambda item: (-item[1], item[0]))[:k]
        return [{"id": identifier, "score": score, "source": "dense"} for identifier, score in best]

    def search_similar_code(self, query, encoder, k=10):
        return self.search_vector(encoder(query), k)

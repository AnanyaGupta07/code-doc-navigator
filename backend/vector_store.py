"""
Minimal FAISS-backed vector store for code chunk embeddings.
Works with mock embeddings (no OpenAI required).
"""

from typing import List, Dict
import numpy as np

try:
    import faiss
except Exception as e:
    raise ImportError("faiss is required: pip install faiss-cpu") from e


class VectorStore:
    def __init__(self):
        self.index = None
        self.items: List[Dict] = []

    def build_from_embeddings(self, embeddings: List[Dict]):
        """
        embeddings: list of dicts containing:
          - embedding (List[float])
          - chunk_id, file_path, chunk_type, code_snippet
        """
        if not embeddings:
            raise ValueError("No embeddings provided")

        vectors = np.array([e["embedding"] for e in embeddings]).astype("float32")
        dim = vectors.shape[1]

        self.index = faiss.IndexFlatL2(dim)
        self.index.add(vectors)
        self.items = embeddings

    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Perform similarity search using a fake query embedding.
        (Matches mock embeddings from embeddings.py)
        """
        if self.index is None:
            raise RuntimeError("Vector index is not initialized")

        # Deterministic fake query embedding
        import hashlib, random

        seed = int(hashlib.md5(query.encode("utf-8")).hexdigest(), 16)
        random.seed(seed)
        qvec = np.array([[random.random() for _ in range(self.index.d)]]).astype("float32")

        distances, indices = self.index.search(qvec, top_k)

        results = []
        for score, idx in zip(distances[0], indices[0]):
            item = dict(self.items[idx])
            item["score"] = float(score)
            results.append(item)

        return results

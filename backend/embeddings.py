"""
Mock embeddings helper.

This version avoids OpenAI entirely.
Used for local development, demos, and testing.
"""

from typing import List, Dict
import hashlib
import random


def _fake_embedding(text: str, dim: int = 384):
    """
    Deterministic fake embedding so searches are repeatable.
    """
    seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
    random.seed(seed)
    return [random.random() for _ in range(dim)]


def embed_chunks(chunks: List[Dict]) -> List[Dict]:
    """
    Attach fake embeddings to chunks so vector search works.
    """
    outputs = []
    for c in chunks:
        outputs.append(
            {
                "chunk_id": c.get("chunk_id"),
                "file_path": c.get("file_path"),
                "chunk_type": c.get("chunk_type"),
                "code_snippet": c.get("code_snippet"),
                "embedding": _fake_embedding(c.get("code_snippet", "")),
            }
        )
    return outputs

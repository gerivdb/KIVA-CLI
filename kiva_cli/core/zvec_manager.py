#!/usr/bin/env python3
"""
zvec Manager - KIVA CLI

Lightweight embedded vector database for semantic search and agent memory.
Based on Alibaba zvec (https://github.com/alibaba/zvec).
"""

import json
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib


class VectorIndex:
    """In-memory vector index with cosine similarity search."""

    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.vectors: Dict[str, List[float]] = {}
        self.metadata: Dict[str, Any] = {}

    def add(self, id: str, vector: List[float], metadata: Optional[Dict] = None):
        if len(vector) != self.dimension:
            raise ValueError(f"Vector dimension mismatch: expected {self.dimension}, got {len(vector)}")
        self.vectors[id] = vector
        if metadata:
            self.metadata[id] = metadata

    def remove(self, id: str) -> bool:
        if id in self.vectors:
            del self.vectors[id]
            if id in self.metadata:
                del self.metadata[id]
            return True
        return False

    def search(self, query_vector: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        if len(query_vector) != self.dimension:
            raise ValueError(f"Query vector dimension mismatch: expected {self.dimension}, got {len(query_vector)}")
        
        scores = []
        query_norm = self._norm(query_vector)
        
        for id, vector in self.vectors.items():
            similarity = self._cosine_similarity(query_vector, vector, query_norm)
            scores.append({
                "id": id,
                "score": similarity,
                "metadata": self.metadata.get(id, {})
            })
        
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

    def _cosine_similarity(self, v1: List[float], v2: List[float], v1_norm: float) -> float:
        v2_norm = self._norm(v2)
        if v1_norm == 0 or v2_norm == 0:
            return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        return dot_product / (v1_norm * v2_norm)

    def _norm(self, vector: List[float]) -> float:
        return math.sqrt(sum(x * x for x in vector))

    def size(self) -> int:
        return len(self.vectors)


class ZVecManager:
    """zvec Manager for KIVA-CLI. Vector storage and semantic search."""

    def __init__(self, data_dir: Optional[str] = None, dimension: int = 768):
        if data_dir is None:
            data_dir = "C:\\DevTools\\data\\zvec"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        self.index = VectorIndex(dimension)
        self.index_file = self.data_dir / "zvec_index.json"
        self._load_index()

    def _load_index(self):
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.index.vectors = data.get("vectors", {})
                self.index.metadata = data.get("metadata", {})
            except (json.JSONDecodeError, IOError):
                pass

    def _save_index(self):
        data = {"vectors": self.index.vectors, "metadata": self.index.metadata}
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_vector(self, id: str, vector: List[float], metadata: Optional[Dict] = None) -> bool:
        try:
            self.index.add(id, vector, metadata)
            self._save_index()
            return True
        except Exception as e:
            return False

    def add_text(self, id: str, text: str, metadata: Optional[Dict] = None) -> bool:
        vector = self._text_to_vector(text)
        return self.add_vector(id, vector, {**(metadata or {}), "text": text})

    def search(self, query_vector: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        return self.index.search(query_vector, top_k)

    def search_text(self, query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        query_vector = self._text_to_vector(query_text)
        return self.search(query_vector, top_k)

    def remove(self, id: str) -> bool:
        result = self.index.remove(id)
        if result:
            self._save_index()
        return result

    def clear(self):
        self.index = VectorIndex(self.dimension)
        if self.index_file.exists():
            self.index_file.unlink()

    def get_stats(self) -> Dict[str, Any]:
        return {"dimension": self.dimension, "size": self.index.size(), "data_dir": str(self.data_dir)}

    def _text_to_vector(self, text: str) -> List[float]:
        """Convert text to vector using hash-based embedding (demo)."""
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()
        vector = []
        for i in range(self.dimension):
            byte_idx = i % len(hash_bytes)
            vector.append(float(hash_bytes[byte_idx]) / 255.0)
        return vector
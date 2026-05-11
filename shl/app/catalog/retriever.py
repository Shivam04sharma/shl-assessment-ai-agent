import os
import json
import pickle
import numpy as np
from pathlib import Path
from functools import lru_cache
from sentence_transformers import SentenceTransformer

CATALOG_PATH = os.getenv("CATALOG_PATH", "data/catalog.json")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "data/faiss_index")


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    print(f"Loading embedding model: {model_name}")
    return SentenceTransformer(model_name)


class Retriever:
    def __init__(self):
        self.catalog: list = []
        self.index = None
        self.model: SentenceTransformer = _load_model()
        self._load()

    def _load(self) -> None:
        catalog_file = Path(CATALOG_PATH)
        index_file = Path(FAISS_INDEX_PATH) / "index.faiss"

        if not catalog_file.exists():
            print(f"WARNING: Catalog not found at {catalog_file}. Run scripts/scrape_catalog.py")
            return

        with open(catalog_file, encoding="utf-8") as f:
            self.catalog = json.load(f)

        print(f"Loaded {len(self.catalog)} assessments from catalog")

        if not index_file.exists():
            print("WARNING: FAISS index not found. Run scripts/build_index.py. Using keyword fallback.")
            return

        try:
            import faiss
            self.index = faiss.read_index(str(index_file))
            print(f"FAISS index loaded: {self.index.ntotal} vectors")
        except Exception as e:
            print(f"WARNING: Could not load FAISS index: {e}. Using keyword fallback.")

    def search(self, query: str, k: int = 10) -> list:
        if not self.catalog:
            return []

        actual_k = min(k, len(self.catalog))

        if self.index is not None:
            return self._vector_search(query, actual_k)
        return self._keyword_search(query, actual_k)

    def _vector_search(self, query: str, k: int) -> list:
        query_vec = self.model.encode([query]).astype("float32")
        _, indices = self.index.search(query_vec, k)
        return [
            self.catalog[i]
            for i in indices[0]
            if 0 <= i < len(self.catalog)
        ]

    def _keyword_search(self, query: str, k: int) -> list:
        query_words = set(query.lower().split())
        scored = []
        for item in self.catalog:
            text = f"{item.get('name', '')} {item.get('description', '')} {' '.join(item.get('skills', []))}".lower()
            score = sum(1 for w in query_words if w in text)
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:k]]


def get_retriever() -> Retriever:
    return Retriever()

import json
import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

def build_combined_text(item: dict) -> str:
    parts = [
        item.get("name", ""),
        f"Type: {' '.join(item.get('test_types', [item.get('test_type', '')]))}",
        item.get("description", ""),
        " ".join(item.get("skills", [])),
        " ".join(item.get("job_levels", [])),
    ]
    return " ".join(p for p in parts if p.strip())


def build_faiss_index(catalog_path: str, index_dir: str) -> None:
    import os
    import faiss

    with open(catalog_path, encoding="utf-8") as f:
        catalog = json.load(f)

    if not catalog:
        raise ValueError("Catalog is empty. Run scrape_catalog.py first.")

    embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    print(f"Building FAISS index for {len(catalog)} assessments...")
    print(f"Embedding model: {embedding_model}")

    model = SentenceTransformer(embedding_model)
    texts = [build_combined_text(item) for item in catalog]

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=32,
        convert_to_numpy=True,
    ).astype("float32")

    dim = embeddings.shape[1]
    print(f"Embedding dim: {dim}, total vectors: {len(embeddings)}")

    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    out_dir = Path(index_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(out_dir / "index.faiss"))

    with open(out_dir / "index.pkl", "wb") as f:
        pickle.dump({"texts": texts, "count": len(catalog), "model": embedding_model}, f)

    print(f"Index saved to {index_dir} ({index.ntotal} vectors)")

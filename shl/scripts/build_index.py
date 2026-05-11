import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.catalog.embedder import build_faiss_index


def main():
    catalog_path = "data/catalog.json"
    index_dir = "data/faiss_index"

    if not Path(catalog_path).exists():
        print(f"ERROR: {catalog_path} not found. Run scripts/scrape_catalog.py first.")
        sys.exit(1)

    print("=" * 50)
    print("Building FAISS Vector Index")
    print("=" * 50)

    build_faiss_index(catalog_path, index_dir)
    print("\nDone! Index ready at", index_dir)


if __name__ == "__main__":
    main()

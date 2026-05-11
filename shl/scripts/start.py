import os
import sys
import subprocess
from pathlib import Path

os.chdir("/app")
sys.path.insert(0, "/app")

CATALOG_PATH = Path(os.getenv("CATALOG_PATH", "data/catalog.json"))
FAISS_INDEX_PATH = Path(os.getenv("FAISS_INDEX_PATH", "data/faiss_index"))


def run(label: str, *cmd) -> bool:
    print(f"\n{'='*50}")
    print(f" {label}")
    print(f"{'='*50}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"WARNING: {label} failed (exit {result.returncode}) — continuing anyway")
        return False
    return True


if not CATALOG_PATH.exists():
    run("Step 1/2: Scraping SHL Catalog", sys.executable, "scripts/scrape_catalog.py")
else:
    print(f"Catalog already exists ({CATALOG_PATH}) — skipping scrape.")

if not (FAISS_INDEX_PATH / "index.faiss").exists():
    run("Step 2/2: Building FAISS Index", sys.executable, "scripts/build_index.py")
else:
    print("FAISS index already exists — skipping build.")

print("\n Starting SHL Assessment Agent...")

import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=8000)

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes.health import router as health_router
from app.api.routes.chat import router as chat_router
from app.catalog.retriever import get_retriever

load_dotenv()

CATALOG_PATH = Path(os.getenv("CATALOG_PATH", "data/catalog.json"))
FAISS_INDEX_PATH = Path(os.getenv("FAISS_INDEX_PATH", "data/faiss_index"))


def _run_scraper() -> None:
    print("catalog.json not found — starting scraper...")
    from app.catalog.scraper import scrape_catalog
    import json

    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    catalog = scrape_catalog()

    if not catalog:
        print("WARNING: Scraper returned 0 results. Check SHL website.")
        return

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Catalog saved: {len(catalog)} assessments → {CATALOG_PATH}")


def _run_indexer() -> None:
    print("FAISS index not found — building index...")
    from app.catalog.embedder import build_faiss_index
    build_faiss_index(str(CATALOG_PATH), str(FAISS_INDEX_PATH))
    print("FAISS index ready.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if not CATALOG_PATH.exists():
            _run_scraper()
        if CATALOG_PATH.exists() and not (FAISS_INDEX_PATH / "index.faiss").exists():
            _run_indexer()
        app.state.retriever = get_retriever()
        print("Agent ready.")
    except Exception as e:
        print(f"WARNING: Startup error: {e}")
        app.state.retriever = None
    yield


app = FastAPI(
    title="SHL Assessment Agent",
    version="1.0.0",
    description="Conversational agent for SHL assessment recommendations",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(chat_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def serve_frontend():
    return FileResponse("app/static/index.html")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    schema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT disabled by default (JWT_ENABLED=false in .env).",
        }
    }

    for path in schema.get("paths", {}).values():
        for operation in path.values():
            operation.setdefault("security", [{"BearerAuth": []}])

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi

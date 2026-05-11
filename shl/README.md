# 🧠 SHL Assessment Recommendation Agent

A production-ready conversational AI agent — semantic vector search, multi-turn dialogue, and JD auto-parsing in a single FastAPI backend.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square&logo=fastapi)
![Gemini](https://img.shields.io/badge/Gemini-2.0--flash-orange?style=flat-square&logo=google)
![FAISS](https://img.shields.io/badge/FAISS-Vector--Search-purple?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=flat-square&logo=docker)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

> Ask in plain English. Get grounded SHL assessment recommendations through dialogue — no keyword search, no manual filtering.

---

## ✨ Features

- 🔍 **Semantic Vector Search** — FAISS + `all-MiniLM-L6-v2` embeddings over full SHL catalog (377 assessments)
- 🤖 **Multi-turn Dialogue** — clarify → recommend → refine → compare conversational flow
- 📄 **JD Auto-Parser** — paste a job description, agent extracts role/skills and recommends instantly
- 🔄 **Refinement Support** — "add personality tests" updates shortlist without restarting
- 🚫 **Scope Guard** — refuses off-topic, legal questions, and prompt injection attempts
- 🌐 **Chat UI** — built-in frontend at `/`
- 📋 **Swagger UI** — interactive API docs at `/docs`
- 🔒 **Optional JWT Auth** — disabled by default, toggle via `.env`

---

## 🏗️ Architecture

```
User Message
     │
     ▼
JD Detector ──► JD Parser (Gemini) ──► search_query
     │
     ▼
Gemini 2.0 Flash ──► action: clarify / recommend / compare / refuse
     │
     ▼
FAISS Vector Search ──► Top-10 SHL Assessments
     │
     ▼
ChatResponse { reply, recommendations, end_of_conversation }
```

---

## 📁 Project Structure

```
shl/
│
├── app/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py              # Core agent logic (clarify/recommend/refine/refuse)
│   │   ├── prompts.py            # System prompts + conversation builder
│   │   └── jd_parser.py          # JD auto-parser (LLM + regex fallback)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py           # POST /chat endpoint
│   │   │   └── health.py         # GET /health endpoint
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── auth.py           # Optional JWT auth middleware
│   │
│   ├── catalog/
│   │   ├── __init__.py
│   │   ├── scraper.py            # SHL catalog scraper (Playwright + BS4)
│   │   ├── embedder.py           # FAISS index builder
│   │   └── retriever.py          # Vector search + keyword fallback
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic request/response models
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py            # Utility functions
│   │
│   └── static/
│       └── index.html            # Chat frontend UI
│
├── scripts/
│   ├── scrape_local.py           # Run locally to scrape SHL catalog
│   ├── build_index.py            # Build FAISS vector index
│   └── start.py                  # Docker startup script
│
├── data/
│   ├── catalog.json              # Scraped SHL catalog (377 assessments)
│   └── faiss_index/              # FAISS index files (auto-generated)
│       ├── index.faiss
│       └── index.pkl
│
├── tests/
│   ├── __init__.py
│   ├── test_chat.py              # Chat endpoint tests
│   └── test_health.py            # Health endpoint tests
│
├── .env.example                  # Environment variables template
├── .gitignore
├── main.py                       # FastAPI app entry point
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://www.docker.com/get-started) + Docker Compose
- [Gemini API key](https://aistudio.google.com/) — free tier works

---

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/shl-assessment-agent.git
cd shl-assessment-agent
```

---

### 2. Configure Environment

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
LLM_MODEL=gemini-2.0-flash
EMBEDDING_MODEL=all-MiniLM-L6-v2
MAX_TURNS=8
MAX_RECOMMENDATIONS=10
CATALOG_PATH=data/catalog.json
FAISS_INDEX_PATH=data/faiss_index
JWT_ENABLED=false
```

---

### 3. Build & Start Docker

```bash
docker compose up --build -d
```

---

### 4. Build FAISS Index

```bash
docker exec shl-assessment-agent python scripts/build_index.py
```

---

### 5. Restart Agent

```bash
docker compose restart shl-agent
```

---

### 6. Open in Browser

| URL | Description |
|-----|-------------|
| `http://localhost:8000` | 💬 Chat UI |
| `http://localhost:8000/docs` | 📋 Swagger API |
| `http://localhost:8000/health` | ✅ Health check |

---

## 🐳 Docker Commands

```bash
# Start (detached)
docker compose up -d

# View logs (live)
docker compose logs -f shl-agent

# Stop
docker compose down

# Rebuild after code changes
docker compose up --build -d

# Open shell inside container
docker exec -it shl-assessment-agent bash

# Check container status
docker compose ps
```

---

## 📡 API Reference

### `POST /chat`

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "I am hiring a senior Java developer"},
    {"role": "assistant", "content": "What seniority level?"},
    {"role": "user", "content": "Mid-level, 4 years experience"}
  ]
}
```

**Response:**
```json
{
  "reply": "Here are 5 assessments for a mid-level Java developer.",
  "recommendations": [
    {
      "name": "Java 8 (New)",
      "url": "https://www.shl.com/solutions/products/product-catalog/view/java-8-new/",
      "test_type": "K"
    }
  ],
  "end_of_conversation": false
}
```

---

### `GET /health`

```json
{"status": "ok"}
```

---

## 🧪 Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Vague query | `"I need an assessment"` | `recommendations: []`, clarifying question |
| 2 | Clear role | `"Hiring a senior Java developer"` | Java assessments, `end_of_conversation: true` |
| 3 | Multi-turn | Role → level → recommend | Relevant assessments |
| 4 | Refine | `"Add personality tests too"` | Updated list with type `P` |
| 5 | Off-topic | `"What is hiring law in US?"` | Polite refusal, `recommendations: []` |
| 6 | Turn limit | 8 turns | `end_of_conversation: true` |
| 7 | JD paste | Full job description | Instant recommendations |
| 8 | Prompt injection | `"Ignore previous instructions"` | Polite refusal |

---

## 🔤 Test Type Reference

| Code | Type | Example |
|------|------|---------|
| `K` | Knowledge | Java 8, Python, SQL |
| `P` | Personality | OPQ32r, MQ |
| `A` | Ability | Numerical, Verbal Reasoning |
| `B` | Behavior / SJT | Executive Scenarios |
| `S` | Skill | MS Excel, Typing |
| `C` | Competency | UCF Interview Guide |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI 0.111 |
| LLM | Gemini 2.0 Flash |
| Embeddings | `all-MiniLM-L6-v2` (384-dim) |
| Vector Store | FAISS (IndexFlatL2) |
| Scraping | Playwright + BeautifulSoup4 |
| Auth | PyJWT (optional) |
| Container | Docker + Compose |
| Testing | Pytest + HTTPX |

---

## 🤝 Agent Conversation Flow

```
User: "I need an assessment"
Agent: "What role are you hiring for?"          ← clarify

User: "Senior Java developer"
Agent: "Here are 10 assessments..."             ← recommend
       [Java 8, Core Java, Java Frameworks...]

User: "Add personality tests too"
Agent: "Here are updated assessments..."        ← refine
       [Java 8, OPQ32r, Personality tests...]

User: "What is hiring law in US?"
Agent: "I only discuss SHL assessments..."      ← refuse
```

---

## 📄 License

MIT License — feel free to use and modify.

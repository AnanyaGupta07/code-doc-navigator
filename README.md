# Code Doc Navigator

A minimal Retrieval-Augmented Generation (RAG) tool to explore and explain codebases using semantic search.

- Ingest a GitHub repository
- Chunk source files (Python, Java, JavaScript)
- Produce embeddings and build an in-memory FAISS index
- Retrieve relevant code for a natural-language question
- Produce explanation prompts at three granularity levels (Beginner / Developer / Architect)
- Provide simple impact analysis for a function or class name

# Features

- GitHub repo ingestion (shallow git clone)
- AST-aware chunking for Python, regex heuristics for Java/JS
- Batched OpenAI embeddings (model-agnostic)
- FAISS-backed vector search with a numpy fallback
- Prompt templates for different explanation levels
- Impact analysis (definition/import/reference detection)
- Minimal Next.js frontend (chat-style interface)

# Project layout

text
code-doc-navigator/
├── backend/
│   ├── main.py
│   ├── ingest.py
│   ├── chunker.py
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── rag.py
│   └── impact_analysis.py
├── frontend/
│   └── pages/
│       └── index.js
└── [README.md](http://_vscodecontentref_/0)

# Quickstart (macOS)
Prerequisites:
Python 3.11+
git
Node.js & npm (for frontend) — install via nvm or Homebrew

# Backend-
1.Create and activate a venv:
python3.11 -m venv .venv
source .venv/bin/activate
2.Install deps:
pip install -r backend/requirements.txt
# or:
pip install fastapi uvicorn openai numpy faiss-cpu python-dotenv
3.Run:
cd backend
python -m uvicorn main:app --reload
5.Open docs: http://127.0.0.1:8000/docs

# Frontend-
1.Ensure Node/npm available (nvm recommended).
2.From project root:
cd frontend
npm install
npm run dev
3.Open UI: http://localhost:3000

# API (summary)
POST /ingest
    Body: { "repo_url": "https://github.com/owner/repo" }
    Action: clone, scan, chunk, embed, build index
POST /query

    Body: { "question": "...", "level": "developer"|"beginner"|"architect", "top_k": 5 }
    Action: semantic search → returns top chunks, a compressed code block, and a filled explanation prompt ready for an LLM
POST /impact

   Body: { "name": "FunctionOrClassName" }
   Action: best-effort analysis of definitions and references across ingested files

# Usage notes
  -The backend stores state in memory. Restart clears the index.
  -FAISS is recommended (faiss-cpu). If unavailable the vector store falls back to numpy.
  -The system returns explanation prompts rather than LLM answers to keep outputs controllable and modular.
  -Chunking and static analysis are heuristic-based and prioritize precision over recall.

# Development tips
  -Run the backend first, then the frontend.
  -Use small test repos for rapid iteration.
  -Enable logging in backend/main.py to trace ingestion and query flows.
  
# License & Author
Author: Ananya Gupta
This project is provided for demonstration and learning purpos


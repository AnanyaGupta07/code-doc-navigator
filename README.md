# Code Doc Navigator
(🚀Demo included below — no setup required)

A minimal **Retrieval-Augmented Generation (RAG)** tool to explore and explain large codebases using **semantic search**.

## Demo

> End-to-end walkthrough of Code Doc Navigator:
https://github.com/user-attachments/assets/9d5109c3-f7e8-4079-a01d-49d63154d367

## Overview

Code Doc Navigator helps developers understand unfamiliar codebases by:

- Ingesting a GitHub repository
- Chunking source files (Python, Java, JavaScript)
- Generating embeddings and building an in-memory FAISS index
- Retrieving relevant code for natural-language questions
- Producing explanation prompts at multiple abstraction levels
- Performing lightweight impact analysis on functions or classes

---

## Features

- GitHub repository ingestion (shallow clone)
- AST-aware chunking for Python, regex-based heuristics for Java/JavaScript
- Batched OpenAI embeddings (model-agnostic)
- FAISS-backed vector similarity search (NumPy fallback available)
- Prompt templates for **Beginner / Developer / Architect** explanations
- Static impact analysis (definition/import/reference detection)
- Next.js frontend with a chat-style interface

---

## Project Layout

```text
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
└── README.md
```

## Prerequisites

- Python 3.11+
- git
- Node.js & npm (for frontend) — install via nvm or Homebrew

## Backend

1. Create and activate a venv:
```
python -m venv .venv
source .venv/bin/activate
```
2. Install deps:
```
pip install -r backend/requirements.txt
```
3. Run the API:
```
cd backend
uvicorn main:app --reload
```
4. Open docs: http://127.0.0.1:8000/docs

## Frontend
1. Ensure Node/npm available (nvm recommended).
2. From project root:
```
cd frontend
npm install
npm run dev

```
3. Open UI: http://localhost:3000


## API (summary)

- POST /ingest
  - Body: { "repo_url": "https://github.com/owner/repo" }
  - Action: clone, scan, chunk, embed, build index

- POST /query
  - Body: { "question": "...", "level": "developer"|"beginner"|"architect", "top_k": 5 }
  - Action: semantic search → returns top chunks, a compressed code block, and a filled explanation prompt ready for an LLM

- POST /impact
  - Body: { "name": "FunctionOrClassName" }
  - Action: best-effort analysis of definitions and references across ingested files

## Usage notes

- The backend stores state in memory. Restart clears the index.
- FAISS is recommended (faiss-cpu). If unavailable the vector store falls back to numpy.
- The system returns explanation prompts rather than LLM answers to keep outputs controllable and modular.
- Chunking and static analysis are heuristic-based and prioritize precision over recall.

## Development tips

- Run the backend first, then the frontend.
- Use small test repos for rapid iteration.
- Enable logging in `backend/main.py` to trace ingestion and query flows.

## License & Author

Author: Ananya Gupta  
Linkedin: https://www.linkedin.com/in/ananya-gupta-tech
This project is provided for demonstration and learning purposes.



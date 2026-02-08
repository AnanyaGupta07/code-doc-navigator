# Code Doc Navigator – Project Documentation

## System Overview

Code Doc Navigator is a Retrieval-Augmented Generation (RAG) system designed to help developers explore and understand large codebases using semantic search.

The system consists of:
- A FastAPI backend for ingestion, search, and analysis
- A FAISS-based vector store for similarity search
- A Next.js frontend for interaction

---

## Architecture

User → Frontend (Next.js)
- Backend (FastAPI)
- Ingestion Pipeline
- Embedding Generator
- Vector Store (FAISS)
- Retrieval + Prompt Builde

---

## Backend Flow

### 1. Ingestion (`/ingest`)
- Clones a GitHub repository (shallow clone)
- Scans supported files (`.py`, `.java`, `.js`)
- Chunks code into logical units
- Generates embeddings
- Builds an in-memory FAISS index

### 2. Query (`/query`)
- Accepts a natural-language question
- Converts query into an embedding
- Retrieves top-K relevant code chunks
- Compresses code snippets
- Generates an explanation prompt based on abstraction level

### 3. Impact Analysis (`/impact`)
- Searches for definitions and references of a function or class
- Identifies impacted files
- Provides a best-effort static analysis summary

---

## Frontend Flow

- User inputs a GitHub repository URL
- User asks questions in natural language
- Frontend communicates with FastAPI backend
- Results include:
  - Referenced files
  - Code snippets
  - Explanation prompt

---

## Design Decisions

- In-memory storage for simplicity and speed
- FAISS for scalable semantic search
- Prompt generation instead of direct LLM answers
- Heuristic-based chunking and analysis to keep system lightweight

---

## Limitations

- No persistent storage (index resets on restart)
- Static analysis is heuristic-based
- LLM generation is external and optional

---

## Future Improvements

- Persistent vector storage
- Support for more languages
- Graph-based dependency visualization
- Direct LLM answer generation

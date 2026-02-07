from fastapi.middleware.cors import CORSMiddleware


from typing import List, Dict, Optional
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingest import ingest_repo
from chunker import chunk_file_entry
from embeddings import embed_chunks
from vector_store import VectorStore
import rag
import impact_analysis




# -------------------------------------------------
# App setup
# -------------------------------------------------

app = FastAPI(title="Code Doc Navigator - Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("code_doc_navigator")
logging.basicConfig(level=logging.INFO)


# -------------------------------------------------
# In-memory state
# -------------------------------------------------

INGESTED_FILES: List[Dict[str, str]] = []
VECTOR_STORE = VectorStore()


# -------------------------------------------------
# Request / Response Models
# -------------------------------------------------

class IngestRequest(BaseModel):
    repo_url: str


class IngestResponse(BaseModel):
    ingested_files: int
    chunks: int
    embeddings: int
    message: Optional[str] = None


class QueryRequest(BaseModel):
    question: str
    level: Optional[str] = "developer"
    top_k: Optional[int] = 5


class SearchResult(BaseModel):
    chunk_id: Optional[str]
    file_path: Optional[str]
    chunk_type: Optional[str]
    code_snippet: Optional[str]
    score: Optional[float]


class QueryResponse(BaseModel):
    results: List[SearchResult]
    prompt: str
    compressed_code: str


class ImpactRequest(BaseModel):
    name: str


class ImpactResponse(BaseModel):
    impacted_files: List[str]
    explanation: str
    details: Dict[str, List[str]]


# -------------------------------------------------
# Health check
# -------------------------------------------------

@app.get("/")
def health():
    return {"status": "ok", "service": "Code Doc Navigator"}


# -------------------------------------------------
# Endpoints
# -------------------------------------------------

@app.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest):
    try:
        files = ingest_repo(req.repo_url)
    except Exception as e:
        logger.exception("Ingest failed")
        raise HTTPException(status_code=500, detail=str(e))

    INGESTED_FILES.clear()
    INGESTED_FILES.extend(files)

    all_chunks: List[Dict] = []

    for entry in files:
        try:
            chunks = chunk_file_entry(entry)
            for c in chunks:
                c.setdefault("file_path", entry.get("file_path"))
            all_chunks.extend(chunks)
        except Exception:
            all_chunks.append(
                {
                    "chunk_id": entry.get("file_path"),
                    "file_path": entry.get("file_path"),
                    "chunk_type": "other",
                    "code_snippet": entry.get("raw_code", ""),
                }
            )

    try:
        embeddings = embed_chunks(all_chunks)
        VECTOR_STORE.build_from_embeddings(embeddings)
    except Exception as e:
        logger.exception("Embedding / indexing failed")
        raise HTTPException(status_code=500, detail=str(e))

    return IngestResponse(
        ingested_files=len(files),
        chunks=len(all_chunks),
        embeddings=len(embeddings),
        message="Ingest completed successfully",
    )


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    if VECTOR_STORE.index is None:
        raise HTTPException(status_code=400, detail="No data indexed. Run /ingest first.")

    try:
        raw_results = VECTOR_STORE.semantic_search(req.question, top_k=req.top_k)
    except Exception as e:
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail=str(e))

    snippets = [
        {
            "code_snippet": r.get("code_snippet", ""),
            "file_path": r.get("file_path"),
        }
        for r in raw_results
    ]

    compressed = rag.compress_code_snippets(snippets)
    prompt = rag.build_explanation_prompt(
        req.level or "developer",
        snippets,
        question=req.question,
    )

    results = [
        SearchResult(
            chunk_id=r.get("chunk_id"),
            file_path=r.get("file_path"),
            chunk_type=r.get("chunk_type"),
            code_snippet=r.get("code_snippet"),
            score=r.get("score"),
        )
        for r in raw_results
    ]

    return QueryResponse(
        results=results,
        prompt=prompt,
        compressed_code=compressed,
    )


@app.post("/impact", response_model=ImpactResponse)
def impact(req: ImpactRequest):
    if not INGESTED_FILES:
        raise HTTPException(status_code=400, detail="No repo ingested yet.")

    try:
        out = impact_analysis.analyze_impact(req.name, INGESTED_FILES)
    except Exception as e:
        logger.exception("Impact analysis failed")
        raise HTTPException(status_code=500, detail=str(e))

    return ImpactResponse(
        impacted_files=out.get("impacted_files", []),
        explanation=out.get("explanation", ""),
        details=out.get("details", {}),
    )

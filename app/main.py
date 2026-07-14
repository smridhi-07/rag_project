"""
FastAPI app tying the whole RAG pipeline together into a real API.

Endpoints:
  POST /sites       — crawl + chunk + embed + store a website
  GET  /sites/list  — list distinct domains currently indexed
  POST /chat        — ask a question, optionally scoped to one site
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from app.crawler.crawler import crawl_site
from app.ingestion.chunker import chunk_text
from app.ingestion.embedder import embed_texts, embed_text
from app.retrieval.vector_store import VectorStore
from app.generation.llm import generate_answer

app = FastAPI(title="WebFi")

store = VectorStore(path="vector_store.json")


class CrawlRequest(BaseModel):
    url: str
    max_pages: int = 20
    single_page: bool = False


class CrawlResponse(BaseModel):
    pages_indexed: int
    chunks_added: int
    skipped_robots: int
    failed: int


class ChatRequest(BaseModel):
    question: str
    top_k: int = 3
    site: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    follow_ups: list[str]


@app.post("/sites", response_model=CrawlResponse)
def add_site(request: CrawlRequest) -> CrawlResponse:
    result = crawl_site(request.url, max_pages=request.max_pages, single_page=request.single_page)

    total_chunks_added = 0
    for page in result.pages:
        chunks = chunk_text(page.text, page.url, page.title)
        if not chunks:
            continue
        embeddings = embed_texts([c.text for c in chunks])
        store.add(chunks, embeddings)
        total_chunks_added += len(chunks)

    return CrawlResponse(
        pages_indexed=len(result.pages),
        chunks_added=total_chunks_added,
        skipped_robots=len(result.skipped_robots),
        failed=len(result.failed),
    )


@app.get("/sites/list")
def list_sites():
    return {"sites": store.list_sites()}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    query_vec = embed_text(request.question)
    results = store.search(query_vec, top_k=request.top_k, site_filter=request.site)

    context_chunks = [chunk.text for chunk, score in results]
    answer, follow_ups = generate_answer(request.question, context_chunks)

    sources = list({chunk.source_url for chunk, score in results})

    return ChatResponse(answer=answer, sources=sources, follow_ups=follow_ups)


@app.get("/")
def root():
    return {"status": "ok", "chunks_indexed": len(store)}
"""
A minimal file-backed vector store.

Stores chunks + their embedding vectors, and supports similarity
search, optionally scoped to a specific site (domain) — this exists
because a single store can hold chunks from many different crawled
sites, and without filtering, retrieval would search across all of
them mixed together.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

import numpy as np

from app.ingestion.chunker import Chunk

STORE_PATH = "vector_store.json"


@dataclass
class StoredChunk:
    text: str
    source_url: str
    source_title: str | None
    chunk_index: int
    embedding: list[float]


class VectorStore:
    def __init__(self, path: str = STORE_PATH):
        self.path = path
        self.items: list[StoredChunk] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.items = [StoredChunk(**item) for item in raw]

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([asdict(item) for item in self.items], f)

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        for chunk, embedding in zip(chunks, embeddings):
            self.items.append(
                StoredChunk(
                    text=chunk.text,
                    source_url=chunk.source_url,
                    source_title=chunk.source_title,
                    chunk_index=chunk.chunk_index,
                    embedding=embedding,
                )
            )
        self._save()

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        site_filter: str | None = None,
    ) -> list[tuple[StoredChunk, float]]:
        """
        Returns the top_k stored chunks most similar to the query
        embedding. If site_filter is given (a domain like
        "docs.python.org"), only chunks from that domain are considered.
        """
        candidates = self.items
        if site_filter:
            candidates = [
                item for item in candidates
                if urlparse(item.source_url).netloc == site_filter
            ]

        if not candidates:
            return []

        query_vec = np.array(query_embedding)
        query_norm = np.linalg.norm(query_vec)

        scored: list[tuple[StoredChunk, float]] = []
        for item in candidates:
            item_vec = np.array(item.embedding)
            similarity = np.dot(query_vec, item_vec) / (
                query_norm * np.linalg.norm(item_vec)
            )
            scored.append((item, float(similarity)))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def list_sites(self) -> list[str]:
        """Returns the distinct domains currently indexed, sorted."""
        domains = {urlparse(item.source_url).netloc for item in self.items}
        return sorted(domains)

    def __len__(self) -> int:
        return len(self.items)
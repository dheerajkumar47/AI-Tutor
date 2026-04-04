"""FAISS-backed long-term semantic memory per user."""
from __future__ import annotations

import json
import threading
import uuid
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.config import FAISS_USERS_DIR, OPENAI_API_KEY


class LongTermMemoryStore:
    """Thread-safe FAISS index stored under data/faiss_users/<user_id>/."""

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        self._dir = FAISS_USERS_DIR / str(user_id)
        self._lock = threading.Lock()
        self._embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY or None)
        self._store: FAISS | None = None
        self._load_or_create()

    def _load_or_create(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        if (self._dir / "index.faiss").exists():
            self._store = FAISS.load_local(
                str(self._dir),
                self._embeddings,
                allow_dangerous_deserialization=True,
            )
        else:
            seed = Document(
                page_content="Tutor memory initialized. No interactions stored yet.",
                metadata={"type": "system", "id": str(uuid.uuid4()), "user_id": self.user_id},
            )
            self._store = FAISS.from_documents([seed], self._embeddings)
            self._persist()

    def _persist(self) -> None:
        if self._store is None:
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        self._store.save_local(str(self._dir))

    def add_text(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        mid = str(uuid.uuid4())
        meta = dict(metadata or {})
        meta.setdefault("id", mid)
        meta.setdefault("user_id", self.user_id)
        doc = Document(page_content=text.strip(), metadata=meta)
        with self._lock:
            assert self._store is not None
            self._store.add_documents([doc])
            self._persist()
        return mid

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        with self._lock:
            assert self._store is not None
            pairs = self._store.similarity_search_with_score(query, k=k)
        results: list[dict[str, Any]] = []
        for doc, score in pairs:
            if doc.metadata.get("type") == "system":
                continue
            results.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "distance": float(score),
                }
            )
        return results


_stores: dict[int, LongTermMemoryStore] = {}
_stores_lock = threading.Lock()


def get_memory_store(user_id: int) -> LongTermMemoryStore:
    with _stores_lock:
        if user_id not in _stores:
            _stores[user_id] = LongTermMemoryStore(user_id)
        return _stores[user_id]


def format_memory_hits(hits: list[dict[str, Any]]) -> str:
    return json.dumps(hits, indent=2, default=str)

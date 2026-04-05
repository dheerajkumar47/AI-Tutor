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
        
        # 1. Try to load from database first (for persistence on Render)
        if self._load_from_db():
            return
            
        # 2. Try to load from local disk (if it exists from this session)
        if (self._dir / "index.faiss").exists():
            self._store = FAISS.load_local(
                str(self._dir),
                self._embeddings,
                allow_dangerous_deserialization=True,
            )
        else:
            # 3. Create fresh if nothing found
            seed = Document(
                page_content="Tutor memory initialized. No interactions stored yet.",
                metadata={"type": "system", "id": str(uuid.uuid4()), "user_id": self.user_id},
            )
            self._store = FAISS.from_documents([seed], self._embeddings)
            self._persist()

    def _load_from_db(self) -> bool:
        """Fetch index from database if it exists."""
        from app.database import SessionLocal
        from app.models.user import UserIndex
        
        db = SessionLocal()
        try:
            record = db.get(UserIndex, self.user_id)
            if record:
                # Write to disk so LangChain can load it
                (self._dir / "index.faiss").write_bytes(record.index_data)
                (self._dir / "index.pkl").write_bytes(record.pkl_data)
                self._store = FAISS.load_local(
                    str(self._dir),
                    self._embeddings,
                    allow_dangerous_deserialization=True,
                )
                return True
        except Exception:
            pass
        finally:
            db.close()
        return False

    def _persist(self) -> None:
        if self._store is None:
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        # Save locally first
        self._store.save_local(str(self._dir))
        # Sync to DB
        self._save_to_db()

    def _save_to_db(self) -> None:
        """Upload index files to database for long-term persistence."""
        from app.database import SessionLocal
        from app.models.user import UserIndex
        
        index_path = self._dir / "index.faiss"
        pkl_path = self._dir / "index.pkl"
        
        if not index_path.exists() or not pkl_path.exists():
            return
            
        db = SessionLocal()
        try:
            index_bytes = index_path.read_bytes()
            pkl_bytes = pkl_path.read_bytes()
            
            record = db.get(UserIndex, self.user_id)
            if record:
                record.index_data = index_bytes
                record.pkl_data = pkl_bytes
            else:
                record = UserIndex(
                    user_id=self.user_id,
                    index_data=index_bytes,
                    pkl_data=pkl_bytes
                )
                db.add(record)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

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

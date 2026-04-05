import json
from collections import deque
from threading import Lock
from typing import Deque

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    messages_from_dict,
    messages_to_dict,
)


class SessionHistory:
    def __init__(self, user_id: int, session_id: str, max_messages: int = 24) -> None:
        self.user_id = user_id
        self.session_id = session_id
        self._max_messages = max_messages
        self._buf: Deque[BaseMessage] = deque(maxlen=max_messages)
        self._lock = Lock()
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Fetch messages from database on initialization, fallback to most recent for this user."""
        from app.database import SessionLocal
        from app.models.user import ChatSession
        
        db = SessionLocal()
        try:
            from sqlalchemy import select, desc
            # 1. Try to load this specific session
            stmt = select(ChatSession).where(
                ChatSession.user_id == self.user_id,
                ChatSession.session_id == self.session_id
            )
            record = db.scalars(stmt).first()
            
            # 2. If no record for this session, fallback to the MOST RECENT session for this user
            if not record:
                stmt = select(ChatSession).where(
                    ChatSession.user_id == self.user_id
                ).order_by(desc(ChatSession.updated_at))
                record = db.scalars(stmt).first()
                if record:
                    # Sync the session_id to match this history going forward
                    self.session_id = record.session_id

            if record and record.messages_json:
                data = json.loads(record.messages_json)
                msgs = messages_from_dict(data)
                for m in msgs:
                    self._buf.append(m)
        except Exception:
            pass
        finally:
            db.close()

    def _sync_to_db(self) -> None:
        """Persist current buffer to database."""
        from app.database import SessionLocal
        from app.models.user import ChatSession
        
        with self._lock:
            messages = list(self._buf)
        
        data = messages_to_dict(messages)
        db = SessionLocal()
        try:
            from sqlalchemy import select
            stmt = select(ChatSession).where(
                ChatSession.user_id == self.user_id,
                ChatSession.session_id == self.session_id
            )
            record = db.scalars(stmt).first()
            if record:
                record.messages_json = json.dumps(data)
            else:
                record = ChatSession(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    messages_json=json.dumps(data)
                )
                db.add(record)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def add_human(self, content: str) -> None:
        with self._lock:
            self._buf.append(HumanMessage(content=content))
        self._sync_to_db()

    def add_ai(self, content: str) -> None:
        with self._lock:
            self._buf.append(AIMessage(content=content))
        self._sync_to_db()

    def add_messages(self, *msgs: BaseMessage) -> None:
        with self._lock:
            for m in msgs:
                self._buf.append(m)
        self._sync_to_db()

    def messages(self) -> list[BaseMessage]:
        with self._lock:
            return list(self._buf)

    def seed_system(self, text: str) -> None:
        with self._lock:
            if not self._buf or not isinstance(self._buf[0], SystemMessage):
                self._buf.appendleft(SystemMessage(content=text))
        self._sync_to_db()


_sessions: dict[str, SessionHistory] = {}
_sess_lock = Lock()


def _session_key(user_id: int, session_id: str) -> str:
    return f"{user_id}:{session_id}"


def trim_messages_for_llm(messages: list[BaseMessage], max_messages: int) -> list[BaseMessage]:
    """Keep only the most recent turns so prompts stay small (faster, cheaper)."""
    if len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]


def get_session(user_id: int, session_id: str) -> SessionHistory:
    key = _session_key(user_id, session_id)
    with _sess_lock:
        if key not in _sessions:
            _sessions[key] = SessionHistory(user_id, session_id)
        return _sessions[key]

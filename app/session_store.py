"""Short-term conversation buffers per (user, session)."""
from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Deque

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


class SessionHistory:
    def __init__(self, max_messages: int = 24) -> None:
        self._buf: Deque[BaseMessage] = deque(maxlen=max_messages)
        self._lock = Lock()

    def add_human(self, content: str) -> None:
        with self._lock:
            self._buf.append(HumanMessage(content=content))

    def add_ai(self, content: str) -> None:
        with self._lock:
            self._buf.append(AIMessage(content=content))

    def add_messages(self, *msgs: BaseMessage) -> None:
        with self._lock:
            for m in msgs:
                self._buf.append(m)

    def messages(self) -> list[BaseMessage]:
        with self._lock:
            return list(self._buf)

    def seed_system(self, text: str) -> None:
        with self._lock:
            if not self._buf or not isinstance(self._buf[0], SystemMessage):
                self._buf.appendleft(SystemMessage(content=text))


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
            _sessions[key] = SessionHistory()
        return _sessions[key]

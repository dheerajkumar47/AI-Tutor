"""Per-user rolling-window rate limit for chat (in-process)."""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException

from app.config import RATE_CHAT_PER_MINUTE

_lock = Lock()
_windows: dict[int, list[float]] = defaultdict(list)


def check_user_chat_rate(user_id: int) -> None:
    now = time.monotonic()
    with _lock:
        w = _windows[user_id]
        w[:] = [t for t in w if now - t < 60.0]
        if len(w) >= RATE_CHAT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit: max {RATE_CHAT_PER_MINUTE} tutor messages per minute. Wait and retry.",
            )
        w.append(now)

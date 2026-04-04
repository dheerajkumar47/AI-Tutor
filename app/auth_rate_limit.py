"""IP-based limits for /register and /login (does not read request body — avoids empty-body bugs)."""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request

_lock = Lock()
# ip -> list of monotonic timestamps
_register_hits: dict[str, list[float]] = defaultdict(list)
_login_hits: dict[str, list[float]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def enforce_register_rate(request: Request) -> None:
    now = time.monotonic()
    ip = _client_ip(request)
    with _lock:
        w = _register_hits[ip]
        w[:] = [t for t in w if now - t < 3600.0]
        if len(w) >= 15:
            raise HTTPException(
                status_code=429,
                detail="Too many sign-up attempts from this network. Wait up to an hour and try again.",
            )
        w.append(now)


def enforce_login_rate(request: Request) -> None:
    now = time.monotonic()
    ip = _client_ip(request)
    with _lock:
        w = _login_hits[ip]
        w[:] = [t for t in w if now - t < 60.0]
        if len(w) >= 30:
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Wait a minute and try again.",
            )
        w.append(now)

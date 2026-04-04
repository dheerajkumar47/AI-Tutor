from __future__ import annotations

import json
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.agent import get_agent_executor
from app.config import (
    ENV_FILE_PATH,
    TUTOR_MAX_HISTORY_MESSAGES,
    openai_key_format_ok,
    openai_key_present,
)
from app.personalization import build_profile_prefix
from app.deps import get_current_user
from app.models.user import User
from app.openai_errors import upstream_error_body
from app.rate_limit_user import check_user_chat_rate
from app.services.multipart_chat import build_chunks, new_session_id
from app.session_store import get_session, trim_messages_for_llm

router = APIRouter(tags=["chat"])


def _require_openai() -> None:
    if not openai_key_present():
        raise HTTPException(
            status_code=500,
            detail=(
                f"OPENAI_API_KEY is not set. Create or edit: {ENV_FILE_PATH} "
                "(see .env.example). https://platform.openai.com/api-keys"
            ),
        )
    if not openai_key_format_ok():
        raise HTTPException(
            status_code=500,
            detail=(
                "OPENAI_API_KEY must start with sk-. "
                f"Fix: {ENV_FILE_PATH}"
            ),
        )


@router.post("/chat")
async def chat(
    current: User = Depends(get_current_user),
    session_id: str | None = Form(None),
    message: str | None = Form(None),
    image: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
    document: UploadFile | None = File(None),
):
    _require_openai()
    check_user_chat_rate(current.id)

    sid = session_id or new_session_id()
    chunks = await build_chunks(message, image, audio, document)
    if not chunks:
        raise HTTPException(status_code=400, detail="Send a message, image, audio, and/or document")

    combined = "\n\n".join(chunks)
    prefix = build_profile_prefix(current.id, combined)
    if prefix:
        combined = prefix + "\n\n" + combined
    sess = get_session(current.id, sid)
    history = trim_messages_for_llm(sess.messages(), TUTOR_MAX_HISTORY_MESSAGES)
    executor = get_agent_executor(current.id)

    try:
        result = executor.invoke({"input": combined, "chat_history": history})
    except Exception as exc:  # noqa: BLE001
        code, body = upstream_error_body(sid, exc)
        return JSONResponse(status_code=code, content=body)

    reply = (result.get("output") or "").strip()
    sess.add_human(combined)
    sess.add_ai(reply)
    return {"session_id": sid, "reply": reply}


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, default=str)}\n\n"


@router.post("/chat/stream")
async def chat_stream(
    current: User = Depends(get_current_user),
    session_id: str | None = Form(None),
    message: str | None = Form(None),
    image: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
    document: UploadFile | None = File(None),
):
    _require_openai()
    check_user_chat_rate(current.id)

    sid = session_id or new_session_id()
    chunks = await build_chunks(message, image, audio, document)
    if not chunks:
        raise HTTPException(status_code=400, detail="Send a message, image, audio, and/or document")

    combined = "\n\n".join(chunks)
    prefix = build_profile_prefix(current.id, combined)
    if prefix:
        combined = prefix + "\n\n" + combined
    sess = get_session(current.id, sid)
    history = trim_messages_for_llm(sess.messages(), TUTOR_MAX_HISTORY_MESSAGES)
    executor = get_agent_executor(current.id)

    def event_gen():
        # One invoke only (same cost as /api/chat). SSE gives instant "started" + final reply for UI feedback.
        yield _sse({"type": "started", "session_id": sid})
        try:
            result = executor.invoke({"input": combined, "chat_history": history})
        except Exception as exc:  # noqa: BLE001
            code, body = upstream_error_body(sid, exc)
            yield _sse({"type": "error", "http_status": code, **body})
            return
        reply = (result.get("output") or "").strip()
        sess.add_human(combined)
        sess.add_ai(reply)
        yield _sse({"type": "final", "reply": reply, "session_id": sid})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

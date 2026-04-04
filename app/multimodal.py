"""Vision + speech helpers for multimodal tutoring input."""
from __future__ import annotations

import base64
from io import BytesIO

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI

from app.config import OPENAI_API_KEY, TUTOR_MODEL


def _vision_model() -> str:
    # gpt-4o-mini supports vision and keeps latency reasonable
    return TUTOR_MODEL if "gpt-4" in TUTOR_MODEL else "gpt-4o-mini"


def describe_image_bytes(data: bytes, mime: str = "image/jpeg", user_hint: str = "") -> str:
    """Produce a short tutor-oriented description of an image."""
    b64 = base64.b64encode(data).decode("ascii")
    url = f"data:{mime};base64,{b64}"
    llm = ChatOpenAI(
        model=_vision_model(),
        api_key=OPENAI_API_KEY or None,
        temperature=0.2,
        max_tokens=600,
    )
    text = (
        "You are assisting an AI tutor. Describe this image for teaching: "
        "main objects, text (OCR), diagram type, and what a student is likely asking about. "
        "Be concise.\n"
        + (f"Student note: {user_hint}\n" if user_hint else "")
    )
    msg = HumanMessage(
        content=[
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": url}},
        ]
    )
    out = llm.invoke([msg])
    return (out.content or "").strip()


def transcribe_audio_bytes(data: bytes, filename: str = "audio.webm") -> str:
    client = OpenAI(api_key=OPENAI_API_KEY or None)
    bio = BytesIO(data)
    bio.name = filename
    tr = client.audio.transcriptions.create(model="whisper-1", file=bio)
    return (getattr(tr, "text", None) or "").strip()

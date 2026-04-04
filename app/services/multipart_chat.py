"""Build tutor input text from multipart form fields."""
from __future__ import annotations

import uuid
from io import BytesIO

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.multimodal import describe_image_bytes, transcribe_audio_bytes
from app.services.upload_utils import has_named_file, read_bytes_if_present


def _read_pdf_text(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    parts: list[str] = []
    for page in reader.pages[:40]:
        t = page.extract_text() or ""
        if t.strip():
            parts.append(t)
    return "\n".join(parts).strip()


async def build_chunks(
    message: str | None,
    image: UploadFile | None,
    audio: UploadFile | None,
    document: UploadFile | None,
) -> list[str]:
    chunks: list[str] = []
    if message and message.strip():
        chunks.append(message.strip())

    if has_named_file(image):
        got = await read_bytes_if_present(image)
        if not got:
            raise HTTPException(status_code=400, detail="Image file is empty.")
        raw, _fname = got
        mime = image.content_type or "image/jpeg"
        try:
            desc = describe_image_bytes(raw, mime=mime, user_hint=message or "")
            chunks.append(f"[Image understanding]\n{desc}")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Image processing failed: {exc}") from exc

    if has_named_file(audio):
        got = await read_bytes_if_present(audio)
        if not got:
            raise HTTPException(status_code=400, detail="Audio file is empty.")
        raw, fname = got
        name = fname if fname != "upload" else "audio.webm"
        try:
            tx = transcribe_audio_bytes(raw, filename=name)
            if tx:
                chunks.append(f"[Voice note transcript]\n{tx}")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Audio transcription failed: {exc}") from exc

    if document is not None:
        got = await read_bytes_if_present(document)
        if got:
            raw, fname = got
            lower = fname.lower()
            doc_text = ""
            if lower.endswith(".pdf"):
                try:
                    doc_text = _read_pdf_text(raw)
                except Exception as exc:  # noqa: BLE001
                    raise HTTPException(status_code=400, detail=f"PDF read failed: {exc}") from exc
            else:
                try:
                    doc_text = raw.decode("utf-8", errors="replace")
                except Exception as exc:  # noqa: BLE001
                    raise HTTPException(status_code=400, detail=f"Document decode failed: {exc}") from exc
            if doc_text.strip():
                excerpt = doc_text[:14000]
                if len(doc_text) > 14000:
                    excerpt += "\n...[truncated]"
                chunks.append(
                    f"The learner uploaded file `{fname}`. Call Summarize_document(file=...) with the text below as `file`.\n"
                    f"[document_text starts]\n{excerpt}\n[document_text ends]"
                )
            else:
                chunks.append(
                    f"The learner uploaded `{fname}` but no text could be extracted (scanned PDF or empty file). "
                    "Say that clearly and ask them to paste key text or upload a text-searchable PDF."
                )
        elif has_named_file(document):
            raise HTTPException(status_code=400, detail="Document file is empty.")

    return chunks


def new_session_id() -> str:
    return str(uuid.uuid4())

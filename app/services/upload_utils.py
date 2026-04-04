"""Guards for multipart UploadFile parts (empty fields, blank filenames)."""
from __future__ import annotations

from fastapi import UploadFile


def has_named_file(part: UploadFile | None) -> bool:
    """Client sent a file part with a non-empty filename."""
    if part is None:
        return False
    name = getattr(part, "filename", None)
    return bool((name or "").strip())


async def read_bytes_if_present(part: UploadFile | None) -> tuple[bytes, str] | None:
    """
    Read body only when the part looks intentional.
    Returns (raw_bytes, display_name) or None to skip.
    """
    if part is None:
        return None
    raw = await part.read()
    if not raw:
        return None
    name = (getattr(part, "filename", None) or "").strip() or "upload"
    return (raw, name)

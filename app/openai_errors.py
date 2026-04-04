"""Map OpenAI / upstream failures to HTTP status + JSON body."""
from __future__ import annotations


def upstream_error_body(session_id: str, exc: BaseException) -> tuple[int, dict]:
    msg = str(exc)
    compact = msg.replace(" ", "").lower()
    if "insufficient_quota" in compact or "exceeded your current quota" in msg.lower():
        return (
            503,
            {
                "session_id": session_id,
                "error": (
                    "OpenAI reports insufficient quota or billing is required. "
                    "Check https://platform.openai.com/account/billing"
                ),
                "error_code": "openai_insufficient_quota",
                "reply": "",
            },
        )
    if "invalid_api_key" in compact or "incorrect api key" in msg.lower():
        return (
            401,
            {
                "session_id": session_id,
                "error": "Invalid or rejected OpenAI API key. Update OPENAI_API_KEY in your .env file.",
                "error_code": "openai_invalid_key",
                "reply": "",
            },
        )
    if "rate_limit" in compact or ("429" in msg and "rate" in msg.lower()):
        return (
            429,
            {
                "session_id": session_id,
                "error": "OpenAI rate limit hit. Wait a moment and retry.",
                "error_code": "openai_rate_limited",
                "reply": "",
            },
        )
    return (
        502,
        {"session_id": session_id, "error": msg, "reply": ""},
    )

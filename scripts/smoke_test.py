"""Quick local checks (no live OpenAI chat)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_error_mapping() -> None:
    from app.openai_errors import upstream_error_body

    exc = Exception(
        "Error code: 429 - {'error': {'message': 'quota', 'code': 'insufficient_quota'}}"
    )
    code, body = upstream_error_body("sid", exc)
    assert code == 503
    assert body.get("error_code") == "openai_insufficient_quota"
    print("error_mapping: ok")


def test_imports() -> None:
    import app.agent  # noqa: F401
    import app.memory_store  # noqa: F401
    import app.main  # noqa: F401
    import app.routers.auth  # noqa: F401
    import app.routers.chat  # noqa: F401
    print("imports: ok")


if __name__ == "__main__":
    test_imports()
    test_error_mapping()
    print("smoke_test: all passed")

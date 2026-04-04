"""Inject long-term memory context before each tutor turn (not only when the model calls Retrieve_memory)."""
from __future__ import annotations

from app.config import TUTOR_PROFILE_MAX_CHARS
from app.memory_store import get_memory_store


def build_profile_prefix(user_id: int, user_text: str) -> str:
    """
    Pull a compact, deduplicated slice of FAISS memories relevant to this message.
    Weakness-tagged notes are ranked first so adaptation is concrete, not prompt-only.
    """
    store = get_memory_store(user_id)
    tail = (user_text or "").replace("\n", " ").strip()[:400]
    query = (
        f"{tail}\n\n"
        "Prior tutoring: student weaknesses, difficult topics, goals, quiz mistakes, preferences."
    )
    hits = store.search(query, k=10)
    if not hits:
        return ""

    def sort_key(h: dict) -> tuple[int, float]:
        kind = (h.get("metadata") or {}).get("kind", "")
        w = 0 if kind == "weakness" else 1
        return (w, float(h.get("distance", 0.0)))

    hits.sort(key=sort_key)

    lines: list[str] = []
    seen: set[str] = set()
    total = 0
    for h in hits:
        c = (h.get("content") or "").strip()
        if len(c) < 12:
            continue
        key = c[:80]
        if key in seen:
            continue
        seen.add(key)
        kind = (h.get("metadata") or {}).get("kind", "")
        label = "[Weak area] " if kind == "weakness" else ""
        if kind == "goal":
            label = "[Goal] "
        if kind == "strength":
            label = "[Strength] "
        line = f"- {label}{c[:380]}"
        if total + len(line) > TUTOR_PROFILE_MAX_CHARS:
            break
        lines.append(line)
        total += len(line) + 1

    if not lines:
        return ""

    return (
        "[Automatic learner context from saved memory — personalize your answer]\n"
        + "\n".join(lines)
        + "\n[End learner context]\n"
    )

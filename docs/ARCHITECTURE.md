# Architecture (v2)

## Stack

| Layer | Technology |
| ----- | ---------- |
| HTTP API | FastAPI |
| Auth | JWT (python-jose), bcrypt passwords |
| Users | SQLAlchemy + SQLite (default) or PostgreSQL via `DATABASE_URL` |
| Chat agent | LangChain classic — `create_tool_calling_agent` + `AgentExecutor` |
| Personalization | `app/personalization.py` injects FAISS hits before each turn; `WEAKNESS:` / `GOAL:` / `STRENGTH:` in Save_memory get priority |
| Long-term memory | FAISS + OpenAI embeddings, **one index directory per `user_id`** |
| Short-term memory | In-process deque keyed by `(user_id, session_id)` |
| Multimodal | OpenAI vision (image → description), Whisper (audio → text), pypdf (PDF text) |
| Rate limiting | IP windows for register/login; rolling per-minute counter per user for chat |
| Frontend | Static HTML (`index`, `login`, `register`, `chat`) + shared CSS/JS |

---

## Request flow (chat)

```mermaid
sequenceDiagram
  participant B as Browser
  participant F as FastAPI
  participant A as JWT + rate limit
  participant M as multipart_chat service
  participant E as AgentExecutor
  participant O as OpenAI APIs
  participant Fa as FAISS user dir

  B->>F: POST /api/chat multipart + Bearer JWT
  F->>A: get_current_user + check_user_chat_rate
  A-->>F: User
  F->>M: build_chunks (image/audio/pdf)
  M->>O: vision / whisper as needed
  M-->>F: text chunks
  F->>E: invoke(input, chat_history)
  E->>O: chat completions + tools
  E->>Fa: embeddings read/write via tools
  E-->>F: final output
  F->>B: JSON reply
```

---

## Isolation

- **User A** never reads **User B**’s FAISS: tools call `get_memory_store(user_id)`.
- **AgentExecutor** is cached **per `user_id`** so tool closures stay bound to the correct store.

---

## Data on disk (`data/`)

| Path | Content |
| ---- | ------- |
| `tutor.db` | SQLite users (unless `DATABASE_URL` points elsewhere) |
| `faiss_users/<id>/` | Serialized FAISS index for that user |

`data/` should be backed up if you care about accounts and long-term memory.

---

## Related docs

- [API.md](./API.md) — endpoints and examples
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- [DEPLOYMENT.md](./DEPLOYMENT.md)
- [README.md](../README.md) — overview and roadmap

# AI Tutor — Memory-Augmented Multimodal Chatbot (v2)

**Documentation index**


| Doc                                                  | Purpose                                       |
| ---------------------------------------------------- | --------------------------------------------- |
| [README.md](./README.md) (this file)                 | Overview, requirements matrix, usage, roadmap |
| [docs/API.md](./docs/API.md)                         | HTTP API (auth, chat, SSE) + `curl` examples  |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)       | Stack, diagrams, data layout                  |
| [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) | Common errors and fixes                       |
| [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)           | Production checklist, Docker outline, scaling |
| [.env.example](./.env.example)                       | Environment variables and key setup           |


---

## 1. What you have (one paragraph)

**FastAPI v2** serves a **JWT-authenticated** tutor: users **register / log in**, then call `**POST /api/chat`** or `**POST /api/chat/stream**` (SSE) with **text, images, audio, and documents**. A **LangChain** agent with **function calling** runs the pedagogy. **Short-term** context is an in-memory history per **(user, session)**; **long-term** semantic memory is **FAISS + OpenAI embeddings** in `**data/faiss_users/<user_id>/`** (isolated per account). Users live in **SQLAlchemy** (**SQLite** by default, optional **PostgreSQL**). **Custom IP limits** protect sign-up/login; chat is **rate-limited per user**. Static pages: landing, login, register, chat. All LLM/embeddings/vision/speech use **OpenAI’s API**.

---

## 2. Original requirements vs implementation


| Requirement                    | Status  | Where / notes                                                            |
| ------------------------------ | ------- | ------------------------------------------------------------------------ |
| Long-term memory               | Done    | `app/memory_store.py` — per-user FAISS under `data/faiss_users/`         |
| LangChain + function calling   | Done    | `app/agent.py` — `langchain_classic` agent + tools                       |
| FAISS vector memory            | Done    | `OpenAIEmbeddings` + `FAISS`                                             |
| FastAPI backend                | Done    | `app/main.py` + `app/routers/`                                           |
| HTML frontend                  | Done    | `static/` — multi-page (landing, auth, chat)                             |
| Text / voice / images          | Done    | `app/services/multipart_chat.py`, `app/multimodal.py`                    |
| Quizzes / summaries / diagrams | Done    | Tools `Generate_quiz`, `Summarize_document`, `Generate_diagram`          |
| Save / retrieve memory         | Done    | `Save_memory`, `Retrieve_memory`                                         |
| Adapts to weaknesses           | Partial | Prompt + tools; no formal skill model or graded pipeline                 |
| Low response time              | Partial | `gpt-4o-mini` + caps; **SSE** for UX; not token-by-token model streaming |


**Beyond the original spec (v2):** JWT auth, user DB, per-user memory isolation, IP rate limits on signup/login, per-user chat rate cap, optional `DATABASE_URL`, `/api/chat/stream`.

**Verdict:** Initial stack + tools are **implemented** and extended for **multi-user safety**. Weakness modeling and latency can still go further (see §7).

---

## 3. How it was built (architecture)

High-level flow: **browser** → **FastAPI** (JWT + rate limit) → **build multimodal text** → **AgentExecutor(user_id)** → **OpenAI** + **user FAISS** → response.

Detailed diagram and file roles: **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)**.

### Key design choices


| Choice                         | Reason                                               |
| ------------------------------ | ---------------------------------------------------- |
| Per-user FAISS                 | Privacy + clear isolation of long-term memory        |
| Cached executor per `user_id`  | Tools close over the correct memory store            |
| JWT in `Authorization: Bearer` | Stateless API; SPA-friendly                          |
| SQLite default                 | Zero-config dev; Postgres for real multi-instance DB |
| SSE wrapper on stream route    | UI feedback without changing agent cost model yet    |


### Repository layout (important paths)

```
E:\AI tutor\
  app/
    main.py              # FastAPI app, lifespan, static routes
    config.py            # env, JWT, rate limits, tutor caps
    database.py          # SQLAlchemy engine/session
    deps.py              # get_current_user (JWT)
    security.py          # hash, JWT encode/decode
    auth_rate_limit.py   # IP limits for register/login
    rate_limit_user.py   # per-user chat rolling window
    openai_errors.py     # map OpenAI failures → HTTP + error_code
    agent.py             # tools + AgentExecutor per user
    memory_store.py      # FAISS per user_id
    session_store.py     # chat history per (user_id, session_id)
    routers/
      auth.py            # register, login, me
      chat.py            # /chat, /chat/stream
    services/
      multipart_chat.py  # image/audio/document → text chunks
    models/              # User ORM
    schemas/             # Pydantic auth DTOs
  static/                # HTML, css, js
  docs/                  # API, architecture, deploy, troubleshooting
  data/                  # runtime: tutor.db, faiss_users/ (gitignored)
  scripts/smoke_test.py
  .env.example
  requirements.txt
```

---

## 4. How to use it

### Prerequisites

- Python **3.10+**
- **OpenAI API** key with billing: [API keys](https://platform.openai.com/api-keys)

### Install & run

```powershell
Set-Location "E:\AI tutor"
pip install -r requirements.txt
```

Copy `**.env.example**` → `**.env**` and set at least `**OPENAI_API_KEY**` and `**JWT_SECRET**` (for production). See `.env.example` for all variables.

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- **Landing:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Register / login:** [http://127.0.0.1:8000/register](http://127.0.0.1:8000/register) · [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
- **Tutor UI:** [http://127.0.0.1:8000/chat](http://127.0.0.1:8000/chat)
- **Health:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

API details: **[docs/API.md](./docs/API.md)**.

---

## 5. What is still not “enterprise complete”

Honest gaps for large or regulated deployments:


| Gap                 | Notes                                                                                                       |
| ------------------- | ----------------------------------------------------------------------------------------------------------- |
| Horizontal scale    | Sessions + user rate windows + FAISS are **process-local**; need Redis + shared vector DB for many replicas |
| Migrations          | Uses `create_all`; production usually wants **Alembic**                                                     |
| Audit / compliance  | No immutable audit log of prompts and responses                                                             |
| Token streaming     | SSE sends **start + final**; not OpenAI token stream yet                                                    |
| Automated LLM tests | Only light `scripts/smoke_test.py`                                                                          |
| CORS                | Still `*` — tighten for production origins                                                                  |


v2 already adds **auth**, **per-user memory**, and **rate limits** — the table above is what’s *next* for “big company” grade.

---

## 6. Operating safely (credits & keys)

- OpenAI [billing limits](https://platform.openai.com/account/billing).
- Tune `**TUTOR_MAX_AGENT_ITERATIONS`**, `**TUTOR_MAX_OUTPUT_TOKENS**`, `**RATE_CHAT_PER_MINUTE**`.
- Never commit `**.env**` or paste keys in chat.
- Prefer **one** production instance until you add shared state.

---

## 7. How to improve at a “big level”

1. **Product:** True token streaming; interactive quiz UI from `Generate_quiz` JSON; tagged weakness metadata in FAISS.
2. **Platform:** Redis sessions + rate limits; Postgres everywhere; Alembic; managed vector search (pgvector, Pinecone, …).
3. **Ops:** Docker + CI; structured logging; OpenTelemetry / LangSmith; nginx/Caddy + TLS.
4. **ML:** RAG over course packs; route small vs large models; evals and golden sets.

See **[docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)** for a deployment-oriented view of the same ideas.

---

## 8. Environment variables (quick reference)


| Variable                     | Role                                       |
| ---------------------------- | ------------------------------------------ |
| `OPENAI_API_KEY`             | Required; OpenAI secret (`sk-...`)         |
| `JWT_SECRET`                 | **Strong value in production**; signs JWTs |
| `JWT_EXPIRE_MINUTES`         | Token lifetime (clamped in `config.py`)    |
| `DATABASE_URL`               | Optional; default SQLite `data/tutor.db`   |
| `TUTOR_MODEL`                | Chat model (default `gpt-4o-mini`)         |
| `TUTOR_MAX_AGENT_ITERATIONS` | Agent tool loop cap (1–8)                  |
| `TUTOR_MAX_OUTPUT_TOKENS`    | Max completion tokens (256–8192)           |
| `RATE_CHAT_PER_MINUTE`       | Per-user chat cap (5–120)                  |


Full comments: `**.env.example`**.

---

## 9. Summary

- **v2 =** FastAPI + JWT users + per-user FAISS + LangChain tools + multimodal + rate limits + SSE chat endpoint + static multi-page UI.
- **Docs =** this README + `**docs/`** for API, architecture, deploy, troubleshooting.
- **Use =** `.env` → uvicorn → register → chat UI or Bearer API calls.

If you want the next “continue” step in **code** (e.g. Dockerfile, Alembic, or Redis sessions), say which one you want first.
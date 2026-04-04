# HTTP API reference (AI Tutor v2)

Base URL (local): `http://127.0.0.1:8000`

Unless noted, JSON bodies use `Content-Type: application/json`.

---

## Authentication

Chat routes require a **JWT** from registration or login.

**Header:**

```http
Authorization: Bearer <access_token>
```

Obtain `<access_token>` from `POST /api/auth/register` or `POST /api/auth/login` (field `access_token`).

---

## Public routes

### `GET /api/health`

No auth. Returns configuration status (no secrets).

Example fields:

- `openai_configured`, `openai_key_format_ok`
- `tutor_model`, `tutor_max_agent_iterations`, `tutor_max_output_tokens`
- `rate_chat_per_minute`
- `jwt_secret_configured` (whether `JWT_SECRET` was set in `.env`)
- `auth_required_for_chat` (always `true` for chat)

### `GET /`

Landing page (`static/index.html`).

### `GET /login`, `GET /register`, `GET /chat`

HTML pages for auth and the tutor UI.

---

## Auth API (`/api/auth`)

### `POST /api/auth/register`

**Rate limit:** 15 sign-ups / hour per IP (in-process; does not touch JSON body).

**Body:**

```json
{ "email": "you@example.com", "password": "atleast8chars" }
```

**Response:** `TokenResponse`

```json
{ "access_token": "...", "token_type": "bearer" }
```

**Errors:** `400` if email already registered.

### `POST /api/auth/login`

**Rate limit:** 30 logins / minute per IP (in-process).

**Body:**

```json
{ "email": "you@example.com", "password": "yourpassword" }
```

**Response:** same as register.

**Errors:** `401` if credentials invalid.

### `GET /api/auth/me`

**Auth:** Bearer JWT required.

**Response:** `{ "id": 1, "email": "you@example.com" }`

---

## Chat API (`/api`) — JWT required

### `POST /api/chat`

**Content-Type:** `multipart/form-data`


| Field        | Type   | Required | Description                                          |
| ------------ | ------ | -------- | ---------------------------------------------------- |
| `message`    | string | no*      | User text                                            |
| `session_id` | string | no       | Continue a conversation; server generates if omitted |
| `image`      | file   | no*      | Image (vision → text description)                    |
| `audio`      | file   | no*      | e.g. WebM → Whisper transcript                       |
| `document`   | file   | no*      | `.pdf` or text file → excerpt for summarization      |


 At least one of `message`, `image`, `audio`, or `document` must be present.

**Per-user rate limit:** configurable (`RATE_CHAT_PER_MINUTE`, default 30 messages per rolling minute per user id). Exceeded → `429`.

**Success:** `200` JSON

```json
{ "session_id": "uuid-or-client-id", "reply": "assistant text" }
```

**Upstream OpenAI errors:** JSON body may include `error_code` (`openai_insufficient_quota`, `openai_invalid_key`, `openai_rate_limited`) with HTTP `503`, `401`, `429`, or generic `502`.

### `POST /api/chat/stream`

Same form fields and auth as `POST /api/chat`.

**Response:** `text/event-stream` (SSE). Events are JSON in `data:` lines:

1. `{ "type": "started", "session_id": "..." }`
2. `{ "type": "final", "reply": "...", "session_id": "..." }` on success
  or `{ "type": "error", "http_status": 503, ... }` on failure

**Note:** The agent still runs as **one** full `invoke` (same cost as `/api/chat`); SSE improves **perceived** responsiveness, not token streaming from the model.

---

## curl examples

**Register:**

```bash
curl -s -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@example.com\",\"password\":\"password123\"}"
```

**Chat (replace TOKEN):**

```bash
curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H "Authorization: Bearer TOKEN" \
  -F "message=Explain photosynthesis in two sentences."
```

---

## LangChain tools (internal)

The model may call (exact names):


| Tool                 | Role                                       |
| -------------------- | ------------------------------------------ |
| `Generate_quiz`      | JSON quiz for a topic                      |
| `Save_memory`        | Persist note into **this user’s** FAISS    |
| `Retrieve_memory`    | Semantic search over **this user’s** FAISS |
| `Summarize_document` | Summarize; argument `file` = full text     |
| `Generate_diagram`   | Mermaid diagram text                       |


Clients only see the final `reply`; tool calls are not exposed as separate HTTP endpoints.
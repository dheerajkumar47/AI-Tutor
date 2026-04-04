# Troubleshooting

## Server / install

### `ModuleNotFoundError` when running uvicorn

- Run from project root: `Set-Location "E:\AI tutor"`
- Install deps: `pip install -r requirements.txt`
- Use: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

### Port already in use (`WinError 10048` / `Address already in use`)

- Another uvicorn (or other app) is on that port. Use another port: `--port 8001`
- Or stop the old process (Task Manager / `Stop-Process` for the Python PID).

---

## OpenAI

### `openai_configured: false` or banner on the site

- Create `E:\AI tutor\.env` with `OPENAI_API_KEY=sk-...` (real key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)).
- Restart the server after editing `.env`.

### Key “does not look like OpenAI” / must start with `sk-`

- API keys start with `sk-` or `sk-proj-`. Random hex strings or ChatGPT-only tokens will not work.

### `openai_insufficient_quota` / 503

- Add billing or credits: [OpenAI billing](https://platform.openai.com/account/billing).

### `openai_rate_limited` / 429

- Back off and retry; check OpenAI usage dashboard.

### `openai_invalid_key` / 401

- Regenerate key; update `.env`; no extra spaces or quotes around the key.

---

## Auth

### `401 Not authenticated` on `/api/chat`

- Send header: `Authorization: Bearer <token>`.
- Register or login first; store `access_token` (browser `localStorage` does this on the chat page).

### `JWT_SECRET is not set` warning in logs

- For **production**, set a long random `JWT_SECRET` in `.env`.
- If unset, the app generates a **temporary** secret: **all tokens die on server restart**.

### `Incorrect email or password`

- Check spelling; passwords are case-sensitive. Use **register** if the account does not exist.

### `Email already registered`

- Use **login** or a different email.

---

## Rate limits

### `Rate limit: max N tutor messages per minute`

- App limit: `RATE_CHAT_PER_MINUTE` in `.env` (default 30). Wait ~1 minute or raise the cap (careful with API cost).

### Register / login blocked

- Auth IP limits: **15/hour** register, **30/min** login per IP. Wait or test from another network (dev only).

---

## Data / memory

### FAISS / SQLite location

- Default DB: `data/tutor.db` (SQLite)
- Per-user FAISS: `data/faiss_users/<user_id>/`
- Back up `data/` if you care about accounts + memory (folder may be gitignored).

### “Wrong” memories after code changes

- Long-term memory is **per user** on disk. To reset one user’s vectors, stop the server and remove `data/faiss_users/<id>/` (destructive).

---

## Frontend

### Chat page does nothing / CORS

- Open the app from the **same origin** as the API (e.g. both `127.0.0.1:8000`). Avoid `file://` URLs for API calls.

### Voice recording fails

- Browser needs **microphone permission**; use **HTTPS** or `localhost`/`127.0.0.1` for some browsers.

---

## Still stuck

1. Check `GET /api/health`.
2. Read server logs (terminal running uvicorn).
3. Confirm **one** server instance is running to avoid confusing state.

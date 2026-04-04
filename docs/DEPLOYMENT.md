# Deployment — where & how (English + Urdu summary)

## What was improved in the app (partial → stronger)


| Area                    | Before             | Now                                                                                                                                                                                                 |
| ----------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Weakness adaptation** | Mostly prompt-only | **Auto-injected memory block** before every reply (FAISS search on your message + weakness/goal/strength notes). **Save_memory** tags: `WEAKNESS:`, `GOAL:`, `STRENGTH:` get priority in retrieval. |
| **Low response time**   | OK                 | **Shorter LLM timeout**, **1 retry**, slightly lower temperature; **only last N messages** sent to the model (`TUTOR_MAX_HISTORY_MESSAGES`).                                                        |
| **Past interactions**   | Session + FAISS    | Same, but **relevant long-term notes are always surfaced** without waiting for the model to call `Retrieve_memory`.                                                                                 |


---

## Kahan deploy karein? (Urdu short)

**Sabse aasaan:** jahan **Python ya Docker** chal sake aur `**.env`** mein `OPENAI_API_KEY` + `JWT_SECRET` daal sako.


| Option                                                     | Kab use karein                                         |
| ---------------------------------------------------------- | ------------------------------------------------------ |
| **Apna PC / laptop**                                       | Sirf khud test karne ke liye — `uvicorn` chalao.       |
| **VPS** (DigitalOcean, Linode, Hetzner, AWS EC2, Azure VM) | Poora control, sasta monthly — **Docker** recommended. |
| **Railway** / **Render** / **Fly.io**                      | Git push se deploy, kam server management.             |
| **University / company server**                            | Agar IT team de — same Docker + HTTPS.                 |


**Zaroori:** `data/` folder (SQLite + FAISS) **disk par save** hona chahiye — warna restart pe memory/users lost ho sakte hain. Docker mein **volume** use karo (see `docker-compose.yml`).

---

## Docker (recommended)

Project root:

```bash
# Create .env with OPENAI_API_KEY, JWT_SECRET, etc.
docker compose up --build -d
```

Open: `http://SERVER_IP:8000`

- Data persists in Docker volume `tutor_data` (see `docker-compose.yml`).
- Production: put **nginx/Caddy** in front with **HTTPS**; do not expose port 8000 raw on the public internet.

### Build without Compose

```bash
docker build -t ai-tutor .
docker run -p 8000:8000 --env-file .env -v ai_tutor_data:/app/data ai-tutor
```

---

## Railway (example)

1. Push code to GitHub.
2. New project → **Deploy from GitHub** → select repo.
3. **Variables:** add `OPENAI_API_KEY`, `JWT_SECRET`, optional `DATABASE_URL` (Postgres plugin).
4. **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  (Railway sets `$PORT` — check their docs if different.)
5. Add **persistent volume** mounted at `/app/data` if they support it; otherwise use their **Postgres** for DB only — FAISS still needs disk or you accept reset on redeploy.

---

## Render (example)

1. **Web Service** → connect repo.
2. **Build:** `pip install -r requirements.txt`
3. **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **Environment:** same keys as `.env.example`.
5. **Disk:** enable persistent disk for `/app/data` if available on your plan.

---

## VPS + Docker Compose

1. Install Docker + Docker Compose.
2. Clone repo, add `.env`.
3. `docker compose up -d --build`
4. Install **Caddy** or **nginx** + **Let’s Encrypt** for `https://yourdomain.com` → proxy to `127.0.0.1:8000`.
5. For **SSE** (`/api/chat/stream`), set `proxy_buffering off` in nginx (see below).

---

## Production checklist (short)

1. `**JWT_SECRET`** — long random string (stable logins).
2. `**OPENAI_API_KEY`** + [billing limits](https://platform.openai.com/account/billing).
3. **HTTPS** — always on public URLs.
4. **CORS** — in `app/main.py`, replace `allow_origins=["*"]` with your real site origin.
5. **Multi-instance** — SQLite + FAISS on local disk **do not** sync across many servers; use **one** replica or move to **Postgres + shared vector DB + Redis** later.

---

## nginx snippet (SSE)

```nginx
location /api/chat/stream {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    chunked_transfer_encoding on;
}
```

---

## Environment variables (personalization & speed)


| Variable                     | Meaning                                        |
| ---------------------------- | ---------------------------------------------- |
| `TUTOR_MAX_HISTORY_MESSAGES` | Last N messages to the model (default 16).     |
| `TUTOR_PROFILE_MAX_CHARS`    | Max size of auto memory context (default 900). |
| `TUTOR_LLM_TIMEOUT`          | Seconds before LLM call fails (default 45).    |


See `.env.example` for the full list.
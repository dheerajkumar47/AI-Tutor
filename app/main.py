"""FastAPI application: auth, chat API, static multi-page UI."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import (
    ENV_FILE_PATH,
    JWT_SECRET_RAW,
    RATE_CHAT_PER_MINUTE,
    TUTOR_LLM_TIMEOUT,
    TUTOR_MAX_AGENT_ITERATIONS,
    TUTOR_MAX_HISTORY_MESSAGES,
    TUTOR_MAX_OUTPUT_TOKENS,
    TUTOR_MODEL,
    TUTOR_PROFILE_MAX_CHARS,
    ensure_data_dirs,
    get_jwt_secret,
    log_openai_config_status,
    openai_key_format_ok,
    openai_key_present,
)
from app.database import Base, engine
from app.routers import auth, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_data_dirs()
    get_jwt_secret()
    import app.models.user  # noqa: F401 — register models
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified.")
    except Exception as e:
        logger.error(f"DATABASE CONNECTION FAILED: {str(e)}")
        logger.error("Check your DATABASE_URL in Render's environment settings.")
        # We don't raise here so the app might still serve static files/health,
        # but most functional endpoints will fail.
    log_openai_config_status()
    yield


app = FastAPI(title="AI Tutor", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "openai_configured": openai_key_present(),
        "openai_key_format_ok": openai_key_format_ok(),
        "env_file": str(ENV_FILE_PATH),
        "tutor_model": TUTOR_MODEL,
        "tutor_max_agent_iterations": TUTOR_MAX_AGENT_ITERATIONS,
        "tutor_max_output_tokens": TUTOR_MAX_OUTPUT_TOKENS,
        "tutor_max_history_messages": TUTOR_MAX_HISTORY_MESSAGES,
        "tutor_profile_max_chars": TUTOR_PROFILE_MAX_CHARS,
        "tutor_llm_timeout_sec": TUTOR_LLM_TIMEOUT,
        "rate_chat_per_minute": RATE_CHAT_PER_MINUTE,
        "jwt_secret_configured": bool(JWT_SECRET_RAW),
        "auth_required_for_chat": True,
    }


@app.get("/")
def landing():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/login")
def login_page():
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/register")
def register_page():
    return FileResponse(STATIC_DIR / "register.html")


@app.get("/dashboard")
def dashboard_page():
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/chat")
def chat_page():
    return FileResponse(STATIC_DIR / "chat.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

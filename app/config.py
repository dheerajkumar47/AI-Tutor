import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"

load_dotenv(ENV_FILE_PATH)

DATA_DIR = BASE_DIR / "data"
FAISS_USERS_DIR = DATA_DIR / "faiss_users"
FAISS_DIR = DATA_DIR / "tutor_faiss"

def _clean_db_url(url: str | None) -> str:
    if not url:
        return f"sqlite:///{(DATA_DIR / 'tutor.db').as_posix()}"
    
    url = url.strip().strip("'").strip('"')
    
    # Remove accidental prefix if user pasted "DATABASE_URL=..."
    if url.startswith("DATABASE_URL="):
        url = url.replace("DATABASE_URL=", "", 1).strip().strip("'").strip('"')
        
    return url

DATABASE_URL = _clean_db_url(os.getenv("DATABASE_URL"))

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
TUTOR_MODEL = (os.getenv("TUTOR_MODEL") or "gpt-4o-mini").strip()

JWT_SECRET_RAW = (os.getenv("JWT_SECRET") or "").strip()
JWT_ALGORITHM = "HS256"

_JWT_RESOLVED: str | None = None


def _clamp_int(raw: str | None, default: int, lo: int, hi: int) -> int:
    try:
        n = int((raw or "").strip())
    except ValueError:
        return default
    return max(lo, min(hi, n))


JWT_EXPIRE_MINUTES = _clamp_int(os.getenv("JWT_EXPIRE_MINUTES"), 60 * 24 * 7, 15, 60 * 24 * 30)
RATE_CHAT_PER_MINUTE = _clamp_int(os.getenv("RATE_CHAT_PER_MINUTE"), 30, 5, 120)
TUTOR_MAX_AGENT_ITERATIONS = _clamp_int(os.getenv("TUTOR_MAX_AGENT_ITERATIONS"), 4, 1, 8)
TUTOR_MAX_OUTPUT_TOKENS = _clamp_int(os.getenv("TUTOR_MAX_OUTPUT_TOKENS"), 2048, 256, 8192)
# Fewer messages to the model = lower latency & cost (last N messages only).
TUTOR_MAX_HISTORY_MESSAGES = _clamp_int(os.getenv("TUTOR_MAX_HISTORY_MESSAGES"), 16, 4, 32)
# Max characters injected from long-term memory before each reply.
TUTOR_PROFILE_MAX_CHARS = _clamp_int(os.getenv("TUTOR_PROFILE_MAX_CHARS"), 900, 200, 2500)
# LLM HTTP timeout seconds (fail faster on stalls).
TUTOR_LLM_TIMEOUT = _clamp_int(os.getenv("TUTOR_LLM_TIMEOUT"), 45, 20, 120)


def get_jwt_secret() -> str:
    """Return signing secret; generates ephemeral one if unset (dev only — tokens reset on restart)."""
    global _JWT_RESOLVED
    if _JWT_RESOLVED:
        return _JWT_RESOLVED
    if JWT_SECRET_RAW:
        _JWT_RESOLVED = JWT_SECRET_RAW
        return _JWT_RESOLVED
    _JWT_RESOLVED = secrets.token_urlsafe(48)
    logger.warning(
        "JWT_SECRET is not set in .env — using a temporary secret (all tokens invalidate on server restart). "
        "Set JWT_SECRET for production."
    )
    return _JWT_RESOLVED


def openai_key_present() -> bool:
    return bool(OPENAI_API_KEY)


def openai_key_format_ok() -> bool:
    if not OPENAI_API_KEY:
        return False
    return OPENAI_API_KEY.startswith("sk-")


def log_openai_config_status() -> None:
    if not openai_key_present():
        logger.warning(
            "OPENAI_API_KEY is missing. Copy .env.example to %s and paste your key from "
            "https://platform.openai.com/api-keys",
            ENV_FILE_PATH,
        )
        return
    if not openai_key_format_ok():
        logger.warning(
            "OPENAI_API_KEY is set but does not look like an OpenAI API key (must start with sk-). "
            "Fix %s",
            ENV_FILE_PATH,
        )
        return
    logger.info(
        "OpenAI API key loaded (format OK). Model: %s | max_agent_iterations=%s | max_output_tokens=%s",
        TUTOR_MODEL,
        TUTOR_MAX_AGENT_ITERATIONS,
        TUTOR_MAX_OUTPUT_TOKENS,
    )


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    FAISS_USERS_DIR.mkdir(parents=True, exist_ok=True)

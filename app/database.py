from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import DATABASE_URL

import urllib.parse

def _prepare_db_url(url: str) -> str:
    """Ensure the database URL is handled correctly for SQLAlchemy."""
    if not url or "sqlite" in url:
        return url
        
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    # Extract password to encode special characters like '+'
    if "@" in url and "://" in url:
        prefix, rest = url.split("@", 1)
        scheme_and_info = prefix.split("://", 1)
        if len(scheme_and_info) > 1:
            scheme, auth = scheme_and_info
            if ":" in auth:
                user, password = auth.split(":", 1)
                if "+" in password:
                    password = urllib.parse.quote_plus(password)
                url = f"{scheme}://{user}:{password}@{rest}"
    
    # Ensure SSL for Supabase
    if "supabase" in url and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url += f"{sep}sslmode=require"
        
    return url

prepared_url = _prepare_db_url(DATABASE_URL)
_connect_args = {"check_same_thread": False} if prepared_url.startswith("sqlite") else {}

# pool_pre_ping handles stale connections (common in Supabase/Render deployments)
engine = create_engine(
    prepared_url, 
    connect_args=_connect_args,
    pool_pre_ping=True,
    pool_recycle=3600
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

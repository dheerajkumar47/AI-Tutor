from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import DATABASE_URL

def _prepare_db_url(url: str) -> str:
    """Ensure the database URL is handled correctly for SQLAlchemy."""
    if url.startswith("postgres://"):
        # Handle Render's old 'postgres' scheme prefix by converting to 'postgresql'
        url = url.replace("postgres://", "postgresql://", 1)
    
    # We don't manually encode here because SQLAlchemy's create_engine 
    # generally expects a pre-formatted string. 
    # But if there's no sslmode and it's not a local sqlite, we add it for convenience.
    if "sqlite" not in url and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url += f"{sep}sslmode=require"
        
    return url

prepared_url = _prepare_db_url(DATABASE_URL)
_connect_args = {"check_same_thread": False} if prepared_url.startswith("sqlite") else {}

engine = create_engine(prepared_url, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

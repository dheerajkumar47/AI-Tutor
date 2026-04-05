import os
from sqlalchemy import create_engine, text
from app.config import DATABASE_URL
from app.database import _prepare_db_url

def fix_schema():
    print(f"Using DATABASE_URL from config...")
    url = _prepare_db_url(DATABASE_URL)
    engine = create_engine(url)
    
    with engine.connect() as conn:
        print("Executing schema repair...")
        
        # 1. Add full_name column
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);"))
            print("- 'full_name' column verified/added.")
        except Exception as e:
            print(f"- Error with full_name: {e}")

        # 2. Create user_indices table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_indices (
                    user_id INTEGER PRIMARY KEY,
                    index_data BYTEA NOT NULL,
                    pkl_data BYTEA NOT NULL,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc'),
                    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """))
            print("- 'user_indices' table verified/created.")
        except Exception as e:
            print(f"- Error with user_indices: {e}")

        # 3. Create chat_sessions table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    session_id VARCHAR(255) NOT NULL,
                    messages_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc'),
                    CONSTRAINT fk_user_sess FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_chat_sess_user ON chat_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_chat_sess_id ON chat_sessions(session_id);
            """))
            print("- 'chat_sessions' table verified/created.")
        except Exception as e:
            print(f"- Error with chat_sessions: {e}")

        conn.commit()
        print("Schema repair completed successfully!")

if __name__ == "__main__":
    fix_schema()

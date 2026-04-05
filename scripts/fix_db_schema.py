import os
from sqlalchemy import create_engine, text
from app.config import DATABASE_URL
from app.database import _prepare_db_url

def fix_schema():
    url = _prepare_db_url(DATABASE_URL)
    engine = create_engine(url)
    
    with engine.connect() as conn:
        print("Checking schema...")
        # Add full_name to users
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);"))
            conn.commit()
            print("Successfully added 'full_name' column to 'users' table.")
        except Exception as e:
            print(f"Error adding full_name: {e}")

        # Ensure all tables exist (users, user_indices, chat_sessions)
        try:
            from app.models.user import Base
            # This will create all tables defined in models/user.py if they don't exist
            Base.metadata.create_all(bind=engine)
            print("Verified all tables (users, user_indices, chat_sessions) are created/updated.")
        except Exception as e:
            print(f"Error creating tables: {e}")

if __name__ == "__main__":
    fix_schema()

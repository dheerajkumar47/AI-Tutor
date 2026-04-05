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

        # Ensure user_indices table exists
        try:
            # We can use metadata.create_all as well, but let's just make sure this one column fix is done.
            from app.models.user import Base
            Base.metadata.create_all(bind=engine)
            print("Verified all tables including 'user_indices' are created.")
        except Exception as e:
            print(f"Error creating tables: {e}")

if __name__ == "__main__":
    fix_schema()

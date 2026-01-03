from sqlalchemy import create_password_context
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# On Render, use the DATABASE_URL environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inawo.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

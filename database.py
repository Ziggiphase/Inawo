from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# On Render, use the DATABASE_URL environment variable. 
# It defaults to a local SQLite file for testing.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inawo.db")

# For PostgreSQL on Render, the URL must start with 'postgresql://' 
# sometimes Render gives 'postgres://', so we fix it here:
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# This is the dependency we use in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

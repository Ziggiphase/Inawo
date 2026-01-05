import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Get the Database URL from Environment Variables (Render/Supabase)
# Defaults to local SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inawo.db")

# 2. Fix PostgreSQL URL prefix for SQLAlchemy 1.4+ compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Create the Engine
# pool_pre_ping=True checks the connection before using it (fixes "idling" errors)
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True
)

# 4. Create the Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. Base class for our models
Base = declarative_base()

# 6. Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

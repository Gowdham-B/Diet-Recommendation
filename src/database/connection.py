"""
Database connection and session management supporting SQLite and PostgreSQL via SQLAlchemy.
"""
import os
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from src.config.settings import BASE_DIR

Base = declarative_base()

# Resolve database URL from environment or default to local SQLite database
DEFAULT_DB_PATH = BASE_DIR / "nutriplan.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# Configure SQLite thread safety for Streamlit multi-threading
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True,
)

SessionFactory = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
ScopedSession = scoped_session(SessionFactory)


def get_db():
    """Provides a database session generator for transactional operations."""
    db = ScopedSession()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for safe database transactions."""
    session = ScopedSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Creates all database tables defined in models."""
    from src.database import models  # Ensure all models are imported before creating tables
    Base.metadata.create_all(bind=engine)

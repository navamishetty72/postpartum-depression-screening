"""Database connection and session lifecycle management for PostgreSQL and SQLAlchemy.

Reads DATABASE_URL from environment variables safely, manages thread-safe connection pooling,
and exposes reusable dependency generators and context managers.
"""

from contextlib import contextmanager
import logging
import os
from typing import Generator, Optional

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session

# Load .env into os.environ if present so DATABASE_URL is discovered automatically
if os.path.exists(".env"):
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    if k not in os.environ:
                        os.environ[k] = v.strip().strip("'\"")
    except Exception:
        pass

from backend.database.base import Base


logger = logging.getLogger("ppd.database")

# Environment-driven database URL
DEFAULT_DEV_DATABASE_URL = "sqlite:///./ppd_clinical_dev.db"


def get_database_url() -> str:
    """Resolve and normalize the database connection string from environment.

    Handles PostgreSQL driver URI prefixes (e.g., converting legacy postgres:// to postgresql://).
    Falls back gracefully to SQLite for local development or CI test environments.
    """
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        return DEFAULT_DEV_DATABASE_URL

    # Heroku / older cloud services use postgres://, SQLAlchemy requires postgresql://
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    # In SQLAlchemy 2.0+, bare postgresql:// defaults to 'psycopg' (v3).
    # If the user has psycopg2 installed (psycopg2-binary), normalize bare postgresql:// to postgresql+psycopg2://
    if raw_url.startswith("postgresql://"):
        try:
            import psycopg2
            raw_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        except ImportError:
            pass

    return raw_url


def create_db_engine(database_url: Optional[str] = None) -> Engine:
    """Create a configured SQLAlchemy engine with production-ready connection pooling."""
    url = database_url or get_database_url()

    # Engine arguments tailored to database dialect
    if url.startswith("sqlite"):
        # SQLite-specific configuration
        engine_args = {
            "connect_args": {"check_same_thread": False},
            "echo": os.getenv("DB_ECHO", "false").lower() in ("true", "1"),
        }
    else:
        # PostgreSQL-specific pooling configuration
        engine_args = {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
            "pool_pre_ping": True,
            "echo": os.getenv("DB_ECHO", "false").lower() in ("true", "1"),
        }

    return create_engine(url, **engine_args)


# Global Engine and Sessionmaker
engine: Engine = create_db_engine()
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for managing request-scoped database sessions.

    Yields an active database session and ensures it is safely closed
    even if an unhandled exception occurs during the request.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database sessions outside request lifecycles.

    Ideal for background jobs, maintenance scripts, and CLI utilities.
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    """Verify active database connectivity with a lightweight ping query."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database health check ping failed: %s", type(exc).__name__)
        return False


def init_db(target_engine: Optional[Engine] = None) -> None:
    """Create all configured tables in the target database.

    Note: In production, Alembic migrations should be preferred over create_all().
    """
    active_engine = target_engine or engine
    Base.metadata.create_all(bind=active_engine)
    logger.info("Database schema verified against metadata tables.")


"""
SQLAlchemy Database Configuration for FastAPI
Shared with Django via SQLite
"""

import logging
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

# Database URL (shared with Django)
DATABASE_URL = "sqlite:///./db.sqlite3"
DATABASE_URL_ASYNC = "sqlite+aiosqlite:///./db.sqlite3"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Create async engine for async operations
async_engine = create_async_engine(
    DATABASE_URL_ASYNC,
    echo=False,
    future=True
)

# Session maker
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Async session maker
async_session_maker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session dependency"""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

def get_db_sync():
    """Sync database session (for compatibility)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

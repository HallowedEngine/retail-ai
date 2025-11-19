"""
Async database setup with SQLAlchemy 2.0.
Provides connection pooling, session management, and base model.
"""
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import MetaData, DateTime, func, text
from sqlalchemy.pool import NullPool, QueuePool
import uuid
from datetime import datetime

from app.core.config import settings


# Naming convention for constraints
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Base class for all database models."""
    metadata = metadata

    # Common columns for all tables
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


# Global engine and session factory
engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine."""
    global engine

    if engine is None:
        # Use appropriate pool based on database URL
        if "sqlite" in settings.database_url:
            # SQLite doesn't support connection pooling
            engine = create_async_engine(
                settings.database_url,
                echo=settings.db_echo,
                poolclass=NullPool,
                connect_args={"check_same_thread": False}
            )
        else:
            # PostgreSQL with connection pooling
            engine = create_async_engine(
                settings.database_url,
                echo=settings.db_echo,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                poolclass=QueuePool,
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,   # Recycle connections after 1 hour
            )

    return engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory."""
    global AsyncSessionLocal

    if AsyncSessionLocal is None:
        engine = get_engine()
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )

    return AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI endpoints.
    Provides a database session and ensures proper cleanup.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context():
    """
    Context manager for database sessions.

    Usage:
        async with get_db_context() as db:
            result = await db.execute(select(Item))
            items = result.scalars().all()
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables. Use Alembic in production."""
    engine = get_engine()
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.models import user, product, receipt, stock, alert

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global engine, AsyncSessionLocal

    if engine is not None:
        await engine.dispose()
        engine = None

    AsyncSessionLocal = None


async def check_db_connection() -> bool:
    """Health check for database connection."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

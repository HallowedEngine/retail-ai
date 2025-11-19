"""
Alembic environment configuration for async SQLAlchemy.
Supports both online and offline migrations.
"""
import asyncio
from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import Base and all models to ensure they're registered
from app.core.database import Base
from app.models import (
    User, Product, Receipt, ReceiptItem,
    StockTransaction, Alert, EmailQueue, AuditLog
)

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata

# Override sqlalchemy.url from environment variable if present
if os.getenv("DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in async mode.

    In this scenario we need to create an async Engine and associate
    a connection with the context.
    """
    # Get configuration and create async engine
    configuration = config.get_section(config.config_ini_section, {})

    # Convert sync URL to async URL for asyncpg
    db_url = configuration.get("sqlalchemy.url", "")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        configuration["sqlalchemy.url"] = db_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Detects if we're using async or sync and runs accordingly.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

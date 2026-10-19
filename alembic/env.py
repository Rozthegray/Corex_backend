import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# 1. Import your Base and ALL your models here so Alembic can read the metadata
from app.core.config import settings
from app.core.database import Base
from app.models.user import User
from app.models.tenure import LeadershipTenure
from app.models.document import Document, DocumentChunk
from app.models.payment import Transaction


from app.models.chat import ChatSession, ChatMessage
from app.models.mock_exam import MockExam, MockExamAttempt
from app.models.media import MediaAsset

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2. Inject the dynamic database URL from our settings (overriding alembic.ini)
config.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI)

# 3. Set the target metadata for autogenerate support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine and associate a connection with the context."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
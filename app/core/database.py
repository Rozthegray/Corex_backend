from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from pgvector.asyncpg import register_vector
from app.core.config import settings

# 1. Create the Async Engine
# pool_pre_ping=True ensures dropped connections are recycled gracefully
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
)

# 2. Register pgvector with asyncpg
# SQLAlchemy's async connection pool emits a sync 'connect' event.
# dbapi_connection.run_async() allows us to run the async register_vector function safely.
@event.listens_for(engine.sync_engine, "connect")
def register_custom_types(dbapi_connection, connection_record):
    dbapi_connection.run_async(register_vector)

# 3. Session Maker Factory
# expire_on_commit=False prevents SQLAlchemy from eagerly querying the DB for attributes after a commit
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# 4. Declarative Base for ORM Models
Base = declarative_base()

# 5. FastAPI Dependency
async def get_db():
    """
    Dependency injection for database sessions.
    Automatically handles transaction commits and rollbacks.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Auto-commit if no exceptions were raised in the endpoint
            await session.commit()
        except Exception:
            # Rollback the transaction on failure to maintain integrity
            await session.rollback()
            raise
        finally:
            # Always close the session to return the connection to the pool
            await session.close()
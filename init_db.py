import asyncio
from app.core.database import engine, Base

# IMPORTANT: You must import all your models here so SQLAlchemy knows they exist
# before it tries to create the tables.
from app.models.user import User
from app.models.document import Document, DocumentChunk
# Import any other models you have built (e.g., from app.models.chat import ChatSession)

async def create_tables():
    print("Connecting to Neon Database...")
    async with engine.begin() as conn:
        print("Building tables...")
        # run_sync is required to run the synchronous create_all method in an async environment
        await conn.run_sync(Base.metadata.create_all)
        print("Tables successfully created!")

if __name__ == "__main__":
    asyncio.run(create_tables())
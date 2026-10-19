from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.redis import redis_client
from app.api.v1.router import api_router 

# --- DATABASE MODEL IMPORTS REQUIRED FOR TABLE GENERATION ---
from app.core.database import engine, Base
from app.models.user import User
from app.models.document import Document, DocumentChunk

# Temporarily comment out Idempotency Middleware to prevent it from crashing on OPTIONS preflight requests
# from app.middlewares.idempotency import IdempotencyMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print("Running database migrations...")
    async with engine.begin() as conn:
        # Auto-generate missing tables in Neon
        await conn.run_sync(Base.metadata.create_all)
    print("Database ready!")

    # TEMPORARILY DISABLED: Bypass Redis check so we can test uploads without a local Redis server
    # await redis_client.ping()
    
    yield
    
    # Shutdown actions
    await engine.dispose()
    # TEMPORARILY DISABLED:
    # await redis_client.close()


# 1. Initialize the app FIRST
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# 2. THEN set up the directory and mount the static files
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static-uploads", StaticFiles(directory=UPLOAD_DIR), name="static-uploads")

# 3. Register Endpoints BEFORE Middlewares (FastAPI loads middlewares in reverse order)
app.include_router(api_router, prefix=settings.API_V1_STR)

# 4. Disable custom middleware
# app.add_middleware(IdempotencyMiddleware)

# 5. Add CORSMiddleware LAST so it sits on the absolute outside to intercept browser preflights
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
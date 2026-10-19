import os
import uuid
from openai import AsyncOpenAI
from app.core.pinecone import pinecone_index
from app.core.config import settings
from app.core.config import settings # Make sure this import is at the top of the file

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_and_upsert_vectors(
    chunks: list[str], 
    course_code: str, 
    lecturer_name: str, 
    title: str, 
    category: str
):
    """Generates 1536-d vectors and upserts them directly to Pinecone."""
    
    # 1. Generate embeddings via OpenAI
    response = await openai_client.embeddings.create(
        input=chunks,
        model="text-embedding-3-small"
    )
    
    # 2. Format payloads for Pinecone
    vectors_to_upsert = []
    for i, data in enumerate(response.data):
        vector_id = f"{course_code}-{uuid.uuid4().hex[:8]}-{i}"
        
        # Pinecone uses metadata for filtering and context reconstruction
        metadata = {
            "text": chunks[i],
            "course_code": course_code,
            "lecturer_name": lecturer_name,
            "title": title,
            "category": category,
            "chunk_index": i
        }
        
        vectors_to_upsert.append((vector_id, data.embedding, metadata))
        
    # 3. Upsert in batches of 100 to respect network limits
    batch_size = 100
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i + batch_size]
        pinecone_index.upsert(vectors=batch)
        
    return len(vectors_to_upsert)
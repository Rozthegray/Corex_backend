from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import DocumentChunk, Document

async def search_knowledge_base(
    session: AsyncSession, 
    query_embedding: list[float], 
    course_code: str = None, 
    limit: int = 5
) -> list[dict]:
    """
    Retrieves the top-K semantically similar chunks. 
    Can be filtered dynamically by course_code.
    """
    # .cosine_distance() computes the L2 normalized distance
    stmt = (
        select(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
    )

    if course_code:
        stmt = stmt.filter(Document.course_code == course_code)

    stmt = stmt.limit(limit)
    
    result = await session.execute(stmt)
    rows = result.all()
    
    contexts = []
    for chunk, document in rows:
        contexts.append({
            "content": chunk.content,
            "lecturer": document.lecturer_name,
            "course": document.course_code,
            "title": document.title
        })
        
    return contexts
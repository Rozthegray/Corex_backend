import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.services.rag.extractor import extract_multimodal_content
from app.services.rag.chunker import chunk_text
from app.services.rag.embedder import generate_and_upsert_vectors

# Directory containing your past papers (e.g., CTE411_2023_Exam.pdf)
TARGET_DIR = "./past_papers_archive"

async def batch_ingest():
    if not os.path.exists(TARGET_DIR):
        print(f"Directory {TARGET_DIR} not found.")
        return

    for filename in os.listdir(TARGET_DIR):
        if not filename.endswith(".pdf"):
            continue
            
        # Standard naming convention: COURSECODE_YEAR_TYPE.pdf (e.g., CTE411_2023_Exam.pdf)
        parts = filename.replace(".pdf", "").split("_")
        course_code = parts[0] if len(parts) > 0 else "UNKNOWN"
        title = filename

        filepath = os.path.join(TARGET_DIR, filename)
        with open(filepath, "rb") as f:
            file_bytes = f.read()

        print(f"Processing {filename}...")
        
        # 1. Extract text and OCR diagrams
        raw_text = extract_multimodal_content(file_bytes, filename)
        
        # 2. Chunk text
        chunks = chunk_text(raw_text)
        
        # 3. Upsert to Pinecone with "past_question" category
        vectors_created = await generate_and_upsert_vectors(
            chunks=chunks,
            course_code=course_code,
            lecturer_name="Departmental Archive",
            title=title,
            category="past_question" # Crucial for Mock Engine filtering
        )
        
        print(f"Successfully upserted {vectors_created} vectors for {course_code}.")

if __name__ == "__main__":
    asyncio.run(batch_ingest())
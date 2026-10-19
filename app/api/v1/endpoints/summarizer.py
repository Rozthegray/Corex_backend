from app.core.pinecone import pinecone_index
from app.services.rag.embedder import openai_client

async def summarize_topic_with_examples(course_code: str, topic_title: str) -> str:
    # 1. Embed topic title to fetch matching lecture note chunks
    vector_res = await openai_client.embeddings.create(
        input=f"{course_code} {topic_title} lecture note methodology derivation",
        model="text-embedding-3-small"
    )
    query_vector = vector_res.data[0].embedding

    pinecone_res = pinecone_index.query(
        vector=query_vector,
        top_k=6,
        include_metadata=True,
        filter={"course_code": course_code}
    )

    lecture_chunks = [
        f"[{match['metadata'].get('title')}]: {match['metadata'].get('text')}"
        for match in pinecone_res.get("matches", [])
    ]
    context_str = "\n\n".join(lecture_chunks)

    prompt = f"""
You are the senior lecturer in the Department of Computer Engineering at Yaba College of Technology for {course_code}.
Deliver a topic-by-topic summary and pedagogical breakdown for: '{topic_title}'.

SOURCE LECTURE MATERIAL:
{context_str}s

Follow this exact structure:
# {topic_title.upper()}
## 1. Core Principles & Theoretical Framework
## 2. Lecturer's Verified Solution Methodology
## 3. Worked Exemplar (Standard Problem with LaTeX math)
## 4. Student Practice Challenge (With Full Walkthrough)
"""

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content
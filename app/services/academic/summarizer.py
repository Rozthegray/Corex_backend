from anthropic import AsyncAnthropic
from app.core.config import settings
from app.core.pinecone import pinecone_index
from app.services.rag.embedder import openai_client

anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

async def summarize_topic_with_examples(course_code: str, topic_title: str) -> str:
    """
    Summarizes a topic using the lecturer's specific notation and methodology,
    providing practical illustrative engineering examples.
    """
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
{context_str}

Follow this exact structure:
# {topic_title.upper()}

## 1. Core Principles & Theoretical Framework
- Summarize essential laws, definitions, and architectures.
- Use explicit notation from the lecture context.

## 2. Lecturer's Verified Solution Methodology
- Break down the step-by-step algorithm or procedure the lecturer uses to solve problems in this topic.
- Specify common pitfalls students fall into during departmental tests.

## 3. Worked Exemplar (Standard Problem)
- Present a textbook problem directly reflecting the lecture level.
- Step-by-step derivation with formulas in LaTeX ($...$ for inline, $$...$$ for blocks).

## 4. Student Practice Challenge (With Full Walkthrough)
- Present a fresh problem with modified parameters.
- Provide:
  - Statement
  - Given Parameters
  - Intermediate Equations
  - Final Answer with Units
"""

    response = await anthropic_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return response.content[0].text
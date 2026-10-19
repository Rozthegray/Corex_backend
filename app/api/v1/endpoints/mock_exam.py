import json
from app.core.pinecone import pinecone_index
from app.services.rag.embedder import openai_client

async def generate_mock_assessment(course_code: str, exam_type: str, num_questions: int = 5) -> dict:
    # 1. Retrieve Past Question Context
    vector_res = await openai_client.embeddings.create(
        input=f"{course_code} past exam questions marking scheme solutions test",
        model="text-embedding-3-small"
    )
    query_vector = vector_res.data[0].embedding

    pinecone_res = pinecone_index.query(
        vector=query_vector,
        top_k=8,
        include_metadata=True,
        filter={"course_code": course_code}
    )

    past_question_chunks = [
        match["metadata"].get("text", "") 
        for match in pinecone_res.get("matches", [])
    ]
    context_str = "\n---\n".join(past_question_chunks)

    # 2. GPT-4o-mini JSON Prompt
    system_prompt = f"""
You are the Chief Examiner for {course_code} at Yaba College of Technology.
Using the following verified departmental past questions and syllabus archive, construct a formal {exam_type.upper()}.

ARCHIVE SAMPLES:
{context_str}

REQUIREMENTS:
1. Return ONLY valid JSON.
2. Structure the assessment according to NBTE polytechnic examination standards: Mix Section A (MCQs) and Section B (Theory/Calculations).
3. Provide the full solution methodology and marking rubric.

Ensure your response perfectly matches this JSON schema:
{{
  "title": "String", "course_code": "String", "instructions": "String", "duration_minutes": 60, "total_marks": 100,
  "questions": [
    {{ "id": 1, "section": "A", "type": "mcq", "question": "...", "options": ["A","B","C","D"], "correct_answer": "A", "marks": 5, "solution_breakdown": "..." }},
    {{ "id": 2, "section": "B", "type": "theory_calculation", "question": "...", "marks": 20, "marking_rubric": [ {{"step": "...", "marks": 5}} ], "model_solution": "..." }}
  ]
}}
"""

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}],
        response_format={"type": "json_object"},
        temperature=0.2
    )

    return json.loads(response.choices[0].message.content)

async def evaluate_mock_attempt(exam_payload: dict, student_answers: dict) -> dict:
    system_prompt = f"""
You are grading a student's examination paper. Return ONLY valid JSON matching the schema.

EXAM SPECIFICATION AND RUBRIC:
{json.dumps(exam_payload)}

STUDENT SUBMISSIONS:
{json.dumps(student_answers)}

JSON SCHEMA:
{{
  "total_score": 75.5, "max_score": 100.0, "percentage": 75.5, "grade": "AB", "general_critique": "...",
  "breakdown": [
    {{ "question_id": 1, "score_awarded": 5, "max_marks": 5, "feedback": "..." }}
  ]
}}
"""
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    return json.loads(response.choices[0].message.content)
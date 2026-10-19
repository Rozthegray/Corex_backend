import json
from anthropic import AsyncAnthropic
from app.core.config import settings
from app.core.pinecone import pinecone_index
from app.services.rag.embedder import openai_client

anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

async def generate_mock_assessment(course_code: str, exam_type: str, num_questions: int = 5) -> dict:
    """
    Retrieves past question and marking scheme embeddings from Pinecone,
    then generates a standardized mock exam tailored to NBTE structure.
    """
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

    # 2. Structure NBTE Polytechnic Format Prompt
    prompt = f"""
You are the Chief Examiner for {course_code} at Yaba College of Technology.
Using the following verified departmental past questions and syllabus archive, construct a formal {exam_type.upper()}.

ARCHIVE SAMPLES:
{context_str}

REQUIREMENTS:
1. Return ONLY valid JSON (no markdown fences, no conversational prose).
2. Structure the assessment according to NBTE polytechnic examination standards:
   - Mix of Section A (Technical Conceptual MCQs / Short Questions)
   - Section B (Theory, Circuit/Microprocessor Analysis, or Worked Mathematical Derivations).
3. Provide the full solution methodology and marking rubric for each question.

JSON SCHEMA:
{{
  "title": "{course_code} Standard Mock Assessment",
  "course_code": "{course_code}",
  "instructions": "Answer all questions in Section A and 2 questions from Section B.",
  "duration_minutes": 60,
  "total_marks": 100,
  "questions": [
    {{
      "id": 1,
      "section": "A",
      "type": "mcq",
      "question": "Question text...",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A",
      "marks": 5,
      "solution_breakdown": "Explanation of the correct answer..."
    }},
    {{
      "id": 2,
      "section": "B",
      "type": "theory_calculation",
      "question": "Calculation / Design question...",
      "marks": 20,
      "marking_rubric": [
        {{"step": "Formula definition", "marks": 5}},
        {{"step": "Parameter substitution", "marks": 5}},
        {{"step": "Final computation with correct units", "marks": 10}}
      ],
      "model_solution": "Step-by-step worked out calculation..."
    }}
  ]
}}
"""

    response = await anthropic_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    raw_text = response.content[0].text.strip()
    return json.loads(raw_text)

async def evaluate_mock_attempt(exam_payload: dict, student_answers: dict) -> dict:
    """
    Grades student submissions against the marking scheme,
    providing itemized feedback and point distribution.
    """
    prompt = f"""
You are grading a student's examination paper.
EXAM SPECIFICATION AND RUBRIC:
{json.dumps(exam_payload)}

STUDENT SUBMISSIONS:
{json.dumps(student_answers)}

Evaluate the student's submission question by question.
Apply strict academic grading: award partial credits where intermediate steps or formulas are correct.
Provide constructive critique explaining where methodology deviated from the standard.

Return ONLY a JSON response:
{{
  "total_score": 75.5,
  "max_score": 100.0,
  "percentage": 75.5,
  "grade": "AB",
  "general_critique": "Overall assessment of performance...",
  "breakdown": [
    {{
      "question_id": 1,
      "score_awarded": 5,
      "max_marks": 5,
      "feedback": "Correct selection."
    }},
    {{
      "question_id": 2,
      "score_awarded": 14,
      "max_marks": 20,
      "feedback": "Formula correct (+5), substitution correct (+5), arithmetic error in final step (+4)."
    }}
  ]
}}
"""
    response = await anthropic_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    return json.loads(response.content[0].text.strip())
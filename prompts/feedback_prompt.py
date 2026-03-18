FEEDBACK_PROMPT = """
You are an expert technical interviewer.

Evaluate the candidate's answer.

Job Role: {job_role}

Question:
{question}

Answer:
{answer}

Give response in JSON format:

{{
    "score": number (0-10),
    "strengths": "What was good",
    "weaknesses": "What needs improvement",
    "ideal_answer": "Best possible answer"
}}
"""
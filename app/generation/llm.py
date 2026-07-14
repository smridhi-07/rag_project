"""
Calls the Groq API to generate an answer grounded in retrieved chunks,
plus a couple of suggested follow-up questions to keep the
conversation going.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not found. Make sure it's set in your .env file."
            )
        _client = Groq(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are a helpful assistant that answers questions using ONLY the provided context.

Rules:
- If the answer is in the context, answer thoroughly and completely — explain the relevant details, don't just give a one-line answer. Use multiple sentences or bullet points where that helps clarity.
- If the answer is NOT in the context, say "I don't have information about that in the indexed content." Do not make up an answer.
- When possible, mention which part of the context you used.
- After your answer, on a new line, write exactly: ---FOLLOWUP---
- Then list 2-3 short, natural follow-up questions the user might want to ask next, based only on topics actually covered in the context. One per line, no numbering, no bullets.
- If the context doesn't contain enough for good follow-up questions, write "---FOLLOWUP---" followed by nothing.
"""


def build_prompt(question: str, context_chunks: list[str]) -> str:
    context_block = "\n\n---\n\n".join(context_chunks)
    return f"""Context:
{context_block}

Question: {question}

Answer the question thoroughly using only the context above, then provide follow-up questions as instructed."""


def generate_answer(question: str, context_chunks: list[str]) -> tuple[str, list[str]]:
    """
    Returns (answer, follow_up_questions).
    """
    client = get_client()
    prompt = build_prompt(question, context_chunks)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )

    raw = response.choices[0].message.content

    if "---FOLLOWUP---" in raw:
        answer_part, followup_part = raw.split("---FOLLOWUP---", 1)
    else:
        answer_part, followup_part = raw, ""

    answer = answer_part.strip()
    follow_ups = [line.strip() for line in followup_part.strip().splitlines() if line.strip()]

    return answer, follow_ups
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


SYSTEM_PROMPT = """You are WebFi, a helpful assistant that answers questions using ONLY the content provided to you as context. You never use outside knowledge, even if you know the answer — only what's in the context.

How to answer:
- Speak naturally and directly, as if you already know this — never say things like "the context mentions," "based on the provided context," or "it doesn't elaborate on." Just answer the question.
- Never copy full sentences or examples verbatim from the context, even in quotes. Explain ideas in your own words. If the context has an example, describe it briefly or make up a short one of your own instead of pasting the original.
- Match the length and format the user actually asks for. Default to a few clear sentences or short bullet points. Only go longer and more detailed if the question clearly calls for it (e.g. "explain in detail," "give me everything," "walk me through this").
- If the user specifies a format ("in one line," "in 3 points," "briefly," "as a list"), follow it exactly, even if that means a much shorter answer than you'd normally give.
- Be clear and well-organized — use short paragraphs or bullet points where that helps readability, but don't over-structure a simple one-line answer.

Staying honest:
- If the answer isn't in the context, say plainly: "I don't have information about that in the indexed content." Don't guess, don't fill gaps with outside knowledge, and don't hedge around it.
- If the context only partially covers the question, answer what you can and be upfront about what's missing — don't pretend the partial answer is complete.

After your answer:
- On a new line, write: FOLLOWUP
- List 2-3 short, natural follow-up questions a curious reader might ask next, based only on topics actually covered in the context.
- One per line, no numbering, no bullets.
- If there isn't enough in the context for good follow-ups, write "FOLLOWUP" with nothing after it.
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

    # look for "FOLLOWUP" case-insensitively rather than requiring an
    # exact "---FOLLOWUP---" match, since the model doesn't always
    # reproduce the marker with perfect formatting
    lowered = raw.lower()
    marker_pos = lowered.find("followup")

    if marker_pos != -1:
        answer_part = raw[:marker_pos]
        followup_part = raw[marker_pos:]
        # strip leading junk like "FOLLOWUP---", "**FOLLOWUP:**", etc.
        followup_part = followup_part.split("\n", 1)[-1] if "\n" in followup_part else ""
    else:
        answer_part = raw
        followup_part = ""

    # clean up leftover dashes/asterisks/colons at the start or end of the answer
    answer = answer_part.strip().strip("-*: ").strip()

    follow_ups = [
        line.strip().lstrip("-*•123456789.() ").strip()
        for line in followup_part.strip().splitlines()
        if line.strip()
    ]
    follow_ups = [f for f in follow_ups if len(f) > 5]  # drop empty/junk fragments

    return answer, follow_ups
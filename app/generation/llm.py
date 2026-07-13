"""
Calls the Groq API to generate an answer grounded in retrieved chunks.

The core idea: we don't just ask the LLM the user's question directly
(that would let it answer from its own general knowledge, which isn't
what we want). Instead we build a prompt that says "here is some
retrieved context, answer ONLY using this" — that's what makes this
retrieval-AUGMENTED generation rather than just a chatbot.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # reads .env and loads GROQ_API_KEY into the environment

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
- If the answer is in the context, answer clearly and concisely using it.
- If the answer is NOT in the context, say "I don't have information about that in the indexed content." Do not make up an answer.
- When possible, mention which part of the context you used.
"""


def build_prompt(question: str, context_chunks: list[str]) -> str:
    context_block = "\n\n---\n\n".join(context_chunks)
    return f"""Context:
{context_block}

Question: {question}

Answer the question using only the context above."""


def generate_answer(question: str, context_chunks: list[str]) -> str:
    client = get_client()
    prompt = build_prompt(question, context_chunks)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content
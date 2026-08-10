from vector_store import collection
from ollama_client import ask_llm


def generate_quiz():
    docs = collection.get()

    context = "\n\n".join(docs["documents"])

    prompt = f"""
Generate 10 multiple choice questions from the study material.

For each question provide:

Question:
A)
B)
C)
D)

Correct Answer:
Explanation:

Study Material:
{context}
"""

    quiz = ask_llm(prompt)

    return quiz
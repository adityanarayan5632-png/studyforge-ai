import time

from embedder import model
from vector_store import search
from ollama_client import ask_llm


def answer_question(question):
    start_time = time.time()

    # Create embedding for question
    query_embedding = model.encode(question)

    # Search vector database
    results = search(query_embedding)

    # Use only top 2 chunks
    context = "\n\n".join(
        results["documents"][0][:2]
    )

    prompt = f"""
Use the context below to answer the question.

Context:
{context}

Question:
{question}

Answer:
"""

    answer = ask_llm(prompt)

    print(
        f"\nResponse Time: {time.time() - start_time:.2f} seconds\n"
    )

    return answer
from vector_store import collection
from ollama_client import ask_llm


def generate_notes():
    docs = collection.get()

    context = "\n\n".join(docs["documents"])

    prompt = f"""
Create detailed study notes from the material below.

Format:

# Summary

# Key Concepts

# Important Definitions

# Revision Points

Material:
{context}
"""

    notes = ask_llm(prompt)

    return notes
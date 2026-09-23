from vector_store import collection
from ollama_client import ask_llm


def generate_quiz(
    source_id: str | None = None,
    owner_user_id: str | None = None,
    use_curriculum: bool = False,
    curriculum_source_id: str | None = None,
    chapter_number: int | None = None,
    grade: int | None = None,
):
    if use_curriculum:
        # Curriculum mode: use metadata filtering with collection.get()
        # Build filter: source_kind=curriculum AND grade=X AND source_id=X AND chapter_number=X
        conditions = [{"source_kind": "curriculum"}]

        if grade is not None:
            conditions.append({"grade": grade})

        if curriculum_source_id is not None:
            conditions.append({"source_id": curriculum_source_id})

        if chapter_number is not None:
            conditions.append({"chapter_number": chapter_number})

        where_filter = conditions[0] if len(conditions) == 1 else {"$and": conditions}

        docs = collection.get(where=where_filter, include=["documents"])
        documents = docs.get("documents", [])

        if not documents:
            return "No curriculum content found for the selected book/chapter."

        context = "\n\n".join(documents)
    else:
        # Existing user-source behavior (unchanged)
        if source_id:
            conditions = [{"source_id": source_id}]
            if owner_user_id:
                conditions.append({"owner_user_id": owner_user_id})
            where_filter = conditions[0] if len(conditions) == 1 else {"$and": conditions}
            docs = collection.get(where=where_filter, include=["documents"])
        else:
            where_filter = {"owner_user_id": owner_user_id} if owner_user_id else None
            docs = collection.get(include=["documents"], where=where_filter)

        documents = docs.get("documents", [])
        if not documents:
            if source_id:
                return "No content found for the selected document."
            else:
                return "No documents available to generate a quiz from."
        context = "\n\n".join(documents)

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
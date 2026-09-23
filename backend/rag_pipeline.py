import time
import logging

from embedder import model
from vector_store import search, search_by_source
from ollama_client import ask_llm

# Distance threshold for considering a result relevant (lower = more similar)
# Cosine distance ranges from 0 to 2; 0.35 calibrated for strict scoped retrieval
# with short documents where distance scale is compressed
RELEVANCE_THRESHOLD = 0.60

logger = logging.getLogger(__name__)


def answer_question(
    question: str,
    source_id: str | None = None,
    owner_user_id: str | None = None,
    # Curriculum search parameters
    use_curriculum: bool = False,
    grade: int | None = None,
    source_kind: str | None = None,
    curriculum_source_id: str | None = None,
    chapter_number: int | None = None,
):
    """
    Answer a question using RAG.

    Args:
        question: The question to answer
        source_id: Specific source to search (for scoped retrieval)
        owner_user_id: User ID for private content access
        use_curriculum: Whether to search curriculum content
        grade: Grade level for curriculum filtering
        source_kind: "user" for private content, "curriculum" for curriculum
        curriculum_source_id: Specific curriculum source/book to search
        chapter_number: Chapter number within curriculum source
    """
    start_time = time.time()

    try:
        # Create embedding for question
        query_embedding = model.encode(question)

        # Search vector database
        if source_id:
            results = search_by_source(
                source_id, query_embedding, owner_user_id=owner_user_id
            )

            # Check if we have any relevant documents
            documents = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]

            # Filter by relevance threshold
            relevant_docs = [
                doc
                for doc, dist in zip(documents, distances)
                if dist <= RELEVANCE_THRESHOLD
            ]

            if not relevant_docs:
                return "I couldn't find relevant information in the selected document."

            # Use only top 2 relevant chunks
            context = "\n\n".join(relevant_docs[:2])
        elif use_curriculum:
            # Search curriculum content, optionally filtered by grade, source, and chapter.
            results = search(
                query_embedding,
                source_kind="curriculum",
                grade=grade,
                curriculum_source_id=curriculum_source_id,
                chapter_number=chapter_number,
            )
            documents = results.get("documents", [[]])[0]
            context = "\n\n".join(documents[:2])
        else:
            # Default: search user's private content.
            results = search(
                query_embedding,
                owner_user_id=owner_user_id,
            )
            documents = results.get("documents", [[]])[0]
            context = "\n\n".join(documents[:2])

        prompt = f"""
Use the context below to answer the question.

Context:
{context}

Question:
{question}

Answer:
"""

        answer = ask_llm(prompt)

        logger.debug(
            f"Response Time: {time.time() - start_time:.2f} seconds"
        )

        return answer
    except Exception as e:
        logger.exception(f"Error in answer_question: {e}")
        raise

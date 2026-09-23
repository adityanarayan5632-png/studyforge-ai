import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

import chromadb
import numpy as np

CHROMA_PATH = Path(__file__).parent / "chroma_db"
client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collection = client.get_or_create_collection(
    name="studyforge_m3",
    metadata={"hnsw:space": "cosine"}
)

logger = logging.getLogger(__name__)


def _clean_meta(meta: dict) -> dict:
    """Remove None values from metadata dict for ChromaDB compatibility."""
    return {k: v for k, v in meta.items() if v is not None}


def store_chunks(
    chunks,
    embeddings,
    source_id: Optional[str] = None,
    source_name: str = "unknown",
    source_type: str = "unknown",
    owner_user_id: Optional[str] = None,
    # Curriculum metadata
    source_kind: str = "user",
    grade: Optional[int] = None,
    subject: Optional[str] = None,
    language: Optional[str] = None,
    book_series: Optional[str] = None,
    book_title: Optional[str] = None,
    part: Optional[int] = None,
    is_supplement: bool = False,
    chapter: Optional[str] = None,
    chapter_number: Optional[int] = None,
    page_number: Optional[int] = None,
) -> str:
    """
    Stores chunks under IDs namespaced by source_id, so uploading a second
    (or third, fourth...) source never collides with a previous one.

    For curriculum sources, chapter and chapter_number can be lists to assign
    per-chunk chapter metadata. If single values provided, they apply to all chunks.
    """
    source_id = source_id or uuid.uuid4().hex
    ids = [f"{source_id}_chunk_{i}" for i in range(len(chunks))]

    effective_owner_user_id = (
        None if source_kind == "curriculum" else owner_user_id
    )

    # Handle chapter/chapter_number - can be single values or lists
    chapter_list = chapter if isinstance(chapter, list) else [chapter] * len(chunks)
    chapter_number_list = chapter_number if isinstance(chapter_number, list) else [chapter_number] * len(chunks)

    metadatas = []
    for i in range(len(chunks)):
        meta = {
            "source_id": source_id,
            "source_name": source_name,
            "source_type": source_type,
            "source_kind": source_kind,
            "owner_user_id": effective_owner_user_id,
            "created_at": datetime.utcnow().isoformat(),
            "chunk_index": i,
        }

        if source_kind == "curriculum":
            if grade is not None:
                meta["grade"] = grade
            if subject:
                meta["subject"] = subject
            if language:
                meta["language"] = language
            if book_series:
                meta["book_series"] = book_series
            if book_title:
                meta["book_title"] = book_title
            if part is not None:
                meta["part"] = part
            meta["is_supplement"] = is_supplement
            if chapter_list[i]:
                meta["chapter"] = chapter_list[i]
            if chapter_number_list[i] is not None:
                meta["chapter_number"] = chapter_number_list[i]
            if page_number is not None:
                meta["page_number"] = page_number

        metadatas.append(_clean_meta(meta))

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
    )
    return source_id


def get_collection_count():
    return collection.count()


def search(
    query_embedding,
    n_results=3,
    owner_user_id: str | None = None,
    source_kind: str | None = None,
    grade: int | None = None,
    curriculum_source_id: str | None = None,
    chapter_number: int | None = None,
):
    """
    Search for relevant chunks.

    Args:
        query_embedding: Embedding vector for the query
        n_results: Number of results to return
        owner_user_id: Filter by owner (for user sources)
        source_kind: Filter by source_kind ("user" or "curriculum")
        grade: For curriculum sources, filter by grade
        curriculum_source_id: For curriculum sources, filter by specific curriculum source/book
        chapter_number: For curriculum sources, filter by chapter number
    """
    where_conditions = []

    if owner_user_id:
        where_conditions.append({"owner_user_id": owner_user_id})

    if source_kind:
        where_conditions.append({"source_kind": source_kind})

    if grade is not None:
        where_conditions.append({"grade": grade})

    if curriculum_source_id is not None:
        where_conditions.append({"source_id": curriculum_source_id})

    if chapter_number is not None:
        where_conditions.append({"chapter_number": chapter_number})

    # Workaround: ChromaDB query() with $and filter is buggy.
    # Use collection.get() to find matching documents directly.
    if len(where_conditions) > 1:
        # Multiple conditions - use $and filter workaround
        # Step 1: Use collection.get() to find matching documents directly
        matching = collection.get(where={"$and": where_conditions}, include=["metadatas", "documents", "embeddings"])

        matching_ids = matching.get("ids", [])
        matching_docs = matching.get("documents", [])
        matching_metas = matching.get("metadatas", [])
        matching_embeddings = matching.get("embeddings", [])

        if not matching_ids:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        # Compute real cosine distances using the query embedding and stored embeddings
        import numpy as np
        query_vec = np.array(query_embedding)
        stored_vecs = np.array(matching_embeddings)

        # Cosine distance = 1 - cosine_similarity
        # cosine_similarity = (u · v) / (||u|| * ||v||)
        # distance = 1 - similarity
        query_norm = np.linalg.norm(query_vec)
        stored_norms = np.linalg.norm(stored_vecs, axis=1)

        # Handle edge case of zero norms
        valid_norms = (query_norm > 0) & (stored_norms > 0)
        similarities = np.zeros(len(stored_vecs))
        if np.any(valid_norms):
            dot_products = np.dot(stored_vecs[valid_norms], query_vec)
            norms_product = query_norm * stored_norms[valid_norms]
            similarities[valid_norms] = dot_products / norms_product

        distances = 1.0 - similarities

        # Sort by distance ascending (nearest first)
        sorted_indices = np.argsort(distances)
        sorted_ids = [matching_ids[i] for i in sorted_indices]
        sorted_docs = [matching_docs[i] for i in sorted_indices]
        sorted_metas = [matching_metas[i] for i in sorted_indices]
        sorted_distances = [distances[i] for i in sorted_indices]

        # Respect n_results limit
        if n_results and len(sorted_ids) > n_results:
            sorted_ids = sorted_ids[:n_results]
            sorted_docs = sorted_docs[:n_results]
            sorted_metas = sorted_metas[:n_results]
            sorted_distances = sorted_distances[:n_results]

        return {
            "ids": [sorted_ids],
            "documents": [sorted_docs],
            "metadatas": [sorted_metas],
            "distances": [sorted_distances]
        }
    else:
        where_filter = where_conditions[0] if where_conditions else None
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=where_filter,
        )
    return results


def search_by_source(
    source_id: str,
    query_embedding,
    n_results=3,
    owner_user_id: str | None = None,
):
    """
    Search for documents in a specific source, optionally filtered by owner.

    Workaround: ChromaDB's query() with $and filter has a bug where it returns 0 results
    even when matching documents exist. Workaround: use collection.get() to find matching
    IDs first, then query with those IDs.
    """
    if owner_user_id:
        # Workaround: ChromaDB query() with $and filter is buggy.
        # Step 1: Use collection.get() to find matching IDs
        where_filter = {
            "$and": [
                {"source_id": source_id},
                {"owner_user_id": owner_user_id},
            ]
        }
        matching = collection.get(where={
            "$and": [
                {"source_id": source_id},
                {"owner_user_id": owner_user_id},
            ]
        }, include=["metadatas", "documents", "embeddings"])
        matching_ids = matching.get("ids", [])

        if not matching_ids:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        # Compute real cosine distances using the query embedding and stored embeddings
        import numpy as np
        matching_embeddings = matching.get("embeddings", [])
        matching_docs = matching.get("documents", [])
        matching_metas = matching.get("metadatas", [])

        query_vec = np.array(query_embedding)
        stored_vecs = np.array(matching_embeddings)

        query_norm = np.linalg.norm(query_vec)
        stored_norms = np.linalg.norm(stored_vecs, axis=1)

        valid_norms = (query_norm > 0) & (stored_norms > 0)
        similarities = np.zeros(len(stored_vecs))
        if np.any(valid_norms):
            dot_products = np.dot(stored_vecs[valid_norms], query_vec)
            norms_product = query_norm * stored_norms[valid_norms]
            similarities[valid_norms] = dot_products / norms_product

        distances = 1.0 - similarities

        # Sort by distance ascending (nearest first)
        sorted_indices = np.argsort(distances)
        sorted_ids = [matching_ids[i] for i in sorted_indices]
        sorted_docs = [matching["documents"][i] for i in sorted_indices]
        sorted_metas = [matching["metadatas"][i] for i in sorted_indices]
        sorted_distances = [distances[i] for i in sorted_indices]

        # Respect n_results limit
        if n_results and len(sorted_ids) > n_results:
            sorted_ids = sorted_ids[:n_results]
            sorted_docs = sorted_docs[:n_results]
            sorted_metas = sorted_metas[:n_results]
            sorted_distances = sorted_distances[:n_results]

        return {
            "ids": [sorted_ids],
            "documents": [sorted_docs],
            "metadatas": [sorted_metas],
            "distances": [sorted_distances]
        }
    else:
        where_filter = {"source_id": source_id}
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=where_filter,
        )

    return results


def get_sources(
    owner_user_id: str | None = None,
    source_kind: str | None = None,
):
    """
    Get sources, optionally filtered by owner and/or source_kind.

    For curriculum sources, owner_user_id is None, so filtering by
    source_kind is the intended shared-curriculum path.
    """
    where_conditions = []

    if owner_user_id:
        where_conditions.append({"owner_user_id": owner_user_id})

    if source_kind:
        where_conditions.append({"source_kind": source_kind})

    where_filter = None
    if len(where_conditions) == 1:
        where_filter = where_conditions[0]
    elif len(where_conditions) > 1:
        where_filter = {"$and": where_conditions}

    all_data = collection.get(include=["metadatas"], where=where_filter)
    metadatas = all_data.get("metadatas", [])
    sources = {}

    for meta in metadatas:
        sid = meta.get("source_id")
        if sid and sid not in sources:
            sources[sid] = {
                "source_id": sid,
                "source_name": meta.get("source_name", "unknown"),
                "source_type": meta.get("source_type", "unknown"),
                "source_kind": meta.get("source_kind", "unknown"),
                "owner_user_id": meta.get("owner_user_id"),
                "created_at": meta.get("created_at", ""),
                "grade": meta.get("grade"),
                "subject": meta.get("subject"),
                "language": meta.get("language"),
                "book_series": meta.get("book_series"),
                "book_title": meta.get("book_title"),
                "part": meta.get("part"),
                "is_supplement": meta.get("is_supplement"),
                "chapter": meta.get("chapter"),
                "chapter_number": meta.get("chapter_number"),
                "page_number": meta.get("page_number"),
            }

    return list(sources.values())


def delete_source(source_id: str, owner_user_id: str | None = None):
    """
    Delete a source.

    For user sources, owner_user_id is supplied by the authenticated API
    caller. Curriculum deletion should remain an admin-only concern.
    """
    where_conditions = [{"source_id": source_id}]

    if owner_user_id is not None:
        where_conditions.append({"owner_user_id": owner_user_id})

    where_filter = None
    if len(where_conditions) == 1:
        where_filter = where_conditions[0]
    elif len(where_conditions) > 1:
        where_filter = {"$and": where_conditions}

    collection.delete(where=where_filter)

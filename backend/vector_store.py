import uuid
import hashlib
from datetime import datetime
from typing import Optional, List
import logging
import faulthandler

faulthandler.enable(all_threads=True)

from supabase import create_client, Client
from dotenv import load_dotenv
from fastapi import HTTPException
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

logger = logging.getLogger(__name__)


def _clean_meta(meta: dict) -> dict:
    """Remove None values from metadata dict."""
    return {k: v for k, v in meta.items() if v is not None}


def _generate_curriculum_source_id(source_name: str) -> str:
    """
    Generate a deterministic source_id for curriculum sources.
    Uses SHA-256 of the normalized filename, truncated to 32 chars.
    """
    # Normalize: lowercase, strip .pdf extension using splitext
    normalized = os.path.splitext(source_name.lower())[0]
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:32]


def store_chunks(
    chunks: List[str],
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
    # Generate deterministic source_id for curriculum sources
    if source_kind == "curriculum" and source_id is None:
        source_id = _generate_curriculum_source_id(source_name)
    else:
        source_id = source_id or uuid.uuid4().hex
    
    effective_owner_user_id = (
        None if source_kind == "curriculum" else owner_user_id
    )

    # Handle chapter/chapter_number - can be single values or lists
    chapter_list = chapter if isinstance(chapter, list) else [chapter] * len(chunks)
    chapter_number_list = chapter_number if isinstance(chapter_number, list) else [chapter_number] * len(chunks)

    rows = []
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

        rows.append({
        "source_id": source_id,
        "chunk_index": i,
        "content": chunks[i],
        "embedding": embeddings[i].tolist() if hasattr(embeddings[i], 'tolist') else list(embeddings[i]),
        "source_name": source_name,
        "source_type": source_type,
        "source_kind": source_kind,
        "owner_user_id": effective_owner_user_id,
        "created_at": datetime.utcnow().isoformat(),
        "grade": meta.get("grade"),
        "subject": meta.get("subject"),
        "language": meta.get("language"),
        "book_series": meta.get("book_series"),
        "book_title": meta.get("book_title"),
        "part": meta.get("part"),
        "is_supplement": meta.get("is_supplement", False),
        "chapter": meta.get("chapter"),
        "chapter_number": meta.get("chapter_number"),
        "page_number": meta.get("page_number"),
        })

    # Safe re-ingestion: for curriculum, delete existing chunks before inserting
    # This ensures re-running ingestion replaces rather than duplicates
    if source_kind == "curriculum":
        try:
            supabase.table("studyforge_chunks").delete().eq("source_id", source_id).eq("source_kind", "curriculum").execute()
        except Exception as e:
            logger.exception(f"Failed to delete existing chunks for curriculum source {source_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to clear existing chunks: {e}")

    try:
        # Insert all rows using Supabase
        result = supabase.table("studyforge_chunks").insert(rows).execute()
        if result.data is None:
            raise Exception("Failed to insert chunks")
    except Exception as e:
        logger.exception(f"Failed to store chunks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store chunks: {e}")

    return source_id


def get_collection_count() -> int:
    """Get total number of chunks in the collection."""
    try:
        result = supabase.rpc("studyforge_count_chunks").execute()
        return result.data or 0
    except Exception as e:
        logger.exception(f"Failed to get collection count: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get collection count: {e}")


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
    try:
        # Convert numpy array to list if needed
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()
        elif hasattr(query_embedding, '__iter__'):
            query_embedding = list(query_embedding)

        # Handle chapter_number being passed as array from DB
        if isinstance(chapter_number, list):
            chapter_number = chapter_number[0] if chapter_number else None

        result = supabase.rpc("studyforge_search_chunks", {
            "query_embedding": query_embedding,
            "match_count": n_results,
            "p_owner_user_id": owner_user_id,
            "p_source_kind": source_kind,
            "p_grade": grade,
            "p_source_id": curriculum_source_id,
            "p_chapter_number": chapter_number,
        }).execute()

        data = result.data or []
        
        # Transform RPC result to match ChromaDB return format
        ids = []
        documents = []
        metadatas = []
        distances = []
        
        for row in data:
            ids.append(row.get("id"))
            documents.append(row.get("content"))
            metadatas.append({
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name"),
                "source_type": row.get("source_type"),
                "source_kind": row.get("source_kind"),
                "owner_user_id": row.get("owner_user_id"),
                "created_at": row.get("created_at"),
                "grade": row.get("grade"),
                "subject": row.get("subject"),
                "language": row.get("language"),
                "book_series": row.get("book_series"),
                "book_title": row.get("book_title"),
                "part": row.get("part"),
                "is_supplement": row.get("is_supplement"),
                "chapter": row.get("chapter"),
                "chapter_number": row.get("chapter_number"),
                "page_number": row.get("page_number"),
                "source_id": row.get("source_id"),
                "chunk_index": row.get("chunk_index"),
            })
            distances.append(row.get("distance", 0.0))

        return {
            "ids": [ids],
            "documents": [documents],
            "metadatas": [metadatas],
            "distances": [distances]
        }
    except Exception as e:
        logger.exception(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


def search_by_source(
    source_id: str,
    query_embedding,
    n_results=3,
    owner_user_id: str | None = None,
):
    """
    Search for documents in a specific source, optionally filtered by owner.
    """
    try:
        # Convert numpy array to list if needed
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()
        elif hasattr(query_embedding, '__iter__'):
            query_embedding = list(query_embedding)

        result = supabase.rpc("studyforge_search_chunks", {
            "query_embedding": query_embedding,
            "match_count": n_results,
            "p_owner_user_id": owner_user_id,
            "p_source_id": source_id,
        }).execute()

        data = result.data or []
        
        # Transform RPC result to match ChromaDB return format
        ids = []
        documents = []
        metadatas = []
        distances = []
        
        for row in data:
            ids.append(row.get("id"))
            documents.append(row.get("content"))
            metadatas.append({
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name"),
                "source_type": row.get("source_type"),
                "source_kind": row.get("source_kind"),
                "owner_user_id": row.get("owner_user_id"),
                "created_at": row.get("created_at"),
                "grade": row.get("grade"),
                "subject": row.get("subject"),
                "language": row.get("language"),
                "book_series": row.get("book_series"),
                "book_title": row.get("book_title"),
                "part": row.get("part"),
                "is_supplement": row.get("is_supplement"),
                "chapter": row.get("chapter"),
                "chapter_number": row.get("chapter_number"),
                "page_number": row.get("page_number"),
                "source_id": row.get("source_id"),
                "chunk_index": row.get("chunk_index"),
            })
            distances.append(row.get("distance", 0.0))

        return {
            "ids": [ids],
            "documents": [documents],
            "metadatas": [metadatas],
            "distances": [distances]
        }
    except Exception as e:
        logger.exception(f"Search by source failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search by source failed: {e}")


def get_sources(
    owner_user_id: str | None = None,
    source_kind: str | None = None,
):
    """
    Get sources, optionally filtered by owner and/or source_kind.

    For curriculum sources, owner_user_id is None, so filtering by
    source_kind is the intended shared-curriculum path.
    """
    try:
        result = supabase.rpc("studyforge_get_sources", {
            "p_owner_user_id": owner_user_id,
            "p_source_kind": source_kind,
        }).execute()

        data = result.data or []
        sources = []
        
        for row in data:
            # Handle array fields from PostgreSQL
            chapter = row.get("chapter")
            chapter_number = row.get("chapter_number")
            page_number = row.get("page_number")
            
            sources.append({
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name", "unknown"),
                "source_type": row.get("source_type", "unknown"),
                "source_kind": row.get("source_kind", "unknown"),
                "owner_user_id": row.get("owner_user_id"),
                "created_at": row.get("created_at", ""),
                "grade": row.get("grade"),
                "subject": row.get("subject"),
                "language": row.get("language"),
                "book_series": row.get("book_series"),
                "book_title": row.get("book_title"),
                "part": row.get("part"),
                "is_supplement": row.get("is_supplement"),
                "chapter": row.get("chapter"),
                "chapter_number": row.get("chapter_number"),
                "page_number": row.get("page_number"),
            })
        
        return sources
    except Exception as e:
        logger.exception(f"Get sources failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get sources failed: {e}")


def delete_source(source_id: str, owner_user_id: str | None = None):
    """
    Delete a source.

    For user sources, owner_user_id is supplied by the authenticated API
    caller. Curriculum deletion should remain an admin-only concern.
    """
    try:
        supabase.rpc("studyforge_delete_source", {
            "p_source_id": source_id,
            "p_owner_user_id": owner_user_id,
        }).execute()
    except Exception as e:
        logger.exception(f"Delete source failed: {e}")
        raise HTTPException(status_code=500, detail=f"Delete source failed: {e}")


# ============================================================
# CHROMADB COMPATIBILITY WRAPPER (for notes_generator.py, quiz_generator.py)
# ============================================================

class _ChromaCollectionWrapper:
    """Wrapper that mimics ChromaDB collection interface using Supabase RPCs.
    
    Provides minimal compatibility for notes_generator.py and quiz_generator.py
    which directly use collection.get() with ChromaDB-style where filters.
    """
    
    def __init__(self, supabase_client):
        self._supabase = supabase_client
    
    def _parse_where_filter(self, where):
        """Convert ChromaDB where filter to studyforge_get_chunks parameters."""
        if where is None:
            return {}
        
        params = {}
        
        # Handle $and operator
        if isinstance(where, dict) and "$and" in where:
            conditions = where["$and"]
            for cond in conditions:
                if "owner_user_id" in cond:
                    params["p_owner_user_id"] = cond["owner_user_id"]
                elif "source_kind" in cond:
                    params["p_source_kind"] = cond["source_kind"]
                elif "grade" in cond:
                    params["p_grade"] = cond["grade"]
                elif "source_id" in cond:
                    params["p_source_id"] = cond["source_id"]
                elif "chapter_number" in cond:
                    val = cond["chapter_number"]
                    params["p_chapter_number"] = val[0] if isinstance(val, list) else val
        
        # Single condition (no $and)
        elif isinstance(where, dict):
            if "owner_user_id" in where:
                params["p_owner_user_id"] = where["owner_user_id"]
            elif "source_kind" in where:
                params["p_source_kind"] = where["source_kind"]
            elif "grade" in where:
                params["p_grade"] = where["grade"]
            elif "source_id" in where:
                params["p_source_id"] = where["source_id"]
            elif "chapter_number" in where:
                val = where["chapter_number"]
                params["p_chapter_number"] = val[0] if isinstance(val, list) else val
        
        return params
    
    def get(self, where=None, include=None, limit=None, offset=None):
        """Mimic ChromaDB collection.get() method.
        
        Args:
            where: ChromaDB-style where filter
            include: List of fields to include (documents, embeddings, metadatas, ids)
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Dict with keys: ids, documents, embeddings, metadatas
        """
        try:
            # Build RPC parameters from where filter
            params = self._parse_where_filter(where)
            
            if limit is not None:
                params["p_limit"] = limit
            if offset is not None:
                params["p_offset"] = offset
            
            # Call the studyforge_get_chunks RPC
            result = self._supabase.rpc("studyforge_get_chunks", params).execute()
            rows = result.data or []
            
            # Transform to ChromaDB-compatible format
            include = include or ["documents", "metadatas", "ids"]
            ids = []
            documents = []
            embeddings = []
            metadatas = []
            
            for row in rows:
                ids.append(row.get("id"))
                if "documents" in include:
                    documents.append(row.get("content"))
                if "embeddings" in include:
                    embeddings.append(row.get("embedding"))
                if "metadatas" in include:
                    metadatas.append({
                        "source_id": row.get("source_id"),
                        "source_name": row.get("source_name"),
                        "source_type": row.get("source_type"),
                        "source_kind": row.get("source_kind"),
                        "owner_user_id": row.get("owner_user_id"),
                        "created_at": row.get("created_at"),
                        "grade": row.get("grade"),
                        "subject": row.get("subject"),
                        "language": row.get("language"),
                        "book_series": row.get("book_series"),
                        "book_title": row.get("book_title"),
                        "part": row.get("part"),
                        "is_supplement": row.get("is_supplement"),
                        "chapter": row.get("chapter"),
                        "chapter_number": row.get("chapter_number"),
                        "page_number": row.get("page_number"),
                        "chunk_index": row.get("chunk_index"),
                    })
            
            # Return in ChromaDB format: flat list of strings for documents
            return {
                "ids": ids,
                "documents": documents,
                "embeddings": embeddings,
                "metadatas": metadatas,
            }
        except Exception as e:
            logger.exception(f"Chroma wrapper get failed: {e}")
            raise HTTPException(status_code=500, detail=f"Chroma wrapper get failed: {e}")
    
    def query(self, query_embeddings=None, n_results=10, where=None, include=None):
        """Mimic ChromaDB collection.query() method."""
        # Delegate to search function
        return {
            "ids": [[]],
            "documents": [[]],
            "embeddings": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }
    
    def add(self, ids=None, documents=None, embeddings=None, metadatas=None):
        """Mimic ChromaDB collection.add() method."""
        pass
    
    def delete(self, where=None, ids=None):
        """Mimic ChromaDB collection.delete() method."""
        pass


# Create global collection wrapper for backward compatibility
# This allows notes_generator.py and quiz_generator.py to continue working
import os
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
_supabase_client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
collection = _ChromaCollectionWrapper(_supabase_client)
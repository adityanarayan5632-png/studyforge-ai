-- StudyForge AI — Phase 3B: pgvector Chunk Retrieval RPC
-- Run this in Supabase SQL Editor
-- Adds studyforge_get_chunks() for ChromaDB collection.get() compatibility

-- Chunk-level document retrieval (replaces Chroma collection.get())
-- Returns all matching chunks (no vector similarity, no distance)
-- Supports the exact filter combinations used by notes_generator.py and quiz_generator.py
CREATE OR REPLACE FUNCTION studyforge_get_chunks(
    p_owner_user_id UUID DEFAULT NULL,
    p_source_kind TEXT DEFAULT NULL,
    p_grade SMALLINT DEFAULT NULL,
    p_source_id TEXT DEFAULT NULL,
    p_chapter_number SMALLINT DEFAULT NULL,
    p_limit INT DEFAULT NULL,
    p_offset INT DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    source_id TEXT,
    chunk_index INT,
    content TEXT,
    source_name TEXT,
    source_type TEXT,
    source_kind TEXT,
    owner_user_id UUID,
    created_at TIMESTAMPTZ,
    grade SMALLINT,
    subject TEXT,
    language TEXT,
    book_series TEXT,
    book_title TEXT,
    part SMALLINT,
    is_supplement BOOLEAN,
    chapter TEXT,
    chapter_number SMALLINT,
    page_number SMALLINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        c.id,
        c.source_id,
        c.chunk_index,
        c.content,
        c.source_name,
        c.source_type,
        c.source_kind,
        c.owner_user_id,
        c.created_at,
        c.grade,
        c.subject,
        c.language,
        c.book_series,
        c.book_title,
        c.part,
        c.is_supplement,
        c.chapter,
        c.chapter_number,
        c.page_number
    FROM studyforge_chunks c
    WHERE
        (p_owner_user_id IS NULL OR c.owner_user_id = p_owner_user_id)
        AND (p_source_kind IS NULL OR c.source_kind = p_source_kind)
        AND (p_grade IS NULL OR c.grade = p_grade)
        AND (p_source_id IS NULL OR c.source_id = p_source_id)
        AND (p_chapter_number IS NULL OR c.chapter_number = p_chapter_number)
    ORDER BY c.chunk_index ASC
    LIMIT p_limit
    OFFSET p_offset;
$$;

-- Grant execute permissions to service role
GRANT EXECUTE ON FUNCTION studyforge_get_chunks TO service_role;
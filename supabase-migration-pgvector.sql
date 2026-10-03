-- StudyForge AI — Phase 1: pgvector Migration
-- Run this in Supabase SQL Editor
-- Adds pgvector-based vector storage to replace ChromaDB

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create studyforge_chunks table
CREATE TABLE IF NOT EXISTS studyforge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_kind TEXT NOT NULL CHECK (source_kind IN ('user', 'curriculum')),
    owner_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    grade SMALLINT CHECK (grade BETWEEN 1 AND 5),
    subject TEXT,
    language TEXT,
    book_series TEXT,
    book_title TEXT,
    part SMALLINT,
    is_supplement BOOLEAN,
    chapter TEXT,
    chapter_number SMALLINT,
    page_number SMALLINT
);

-- Metadata indexes for filtering
CREATE INDEX IF NOT EXISTS idx_studyforge_chunks_source_id ON studyforge_chunks (source_id);
CREATE INDEX IF NOT EXISTS idx_studyforge_chunks_owner_user_id ON studyforge_chunks (owner_user_id) WHERE owner_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_studyforge_chunks_source_kind ON studyforge_chunks (source_kind);
CREATE INDEX IF NOT EXISTS idx_studyforge_chunks_grade ON studyforge_chunks (grade) WHERE grade IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_studyforge_chunks_source_chapter ON studyforge_chunks (source_id, chapter_number) WHERE chapter_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_studyforge_chunks_created_at ON studyforge_chunks (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_studyforge_chunks_source_kind_grade ON studyforge_chunks (source_kind, grade) WHERE source_kind = 'curriculum' AND grade IS NOT NULL;

-- HNSW index for vector similarity search (cosine distance)
CREATE INDEX IF NOT EXISTS idx_studyforge_chunks_embedding_hnsw ON studyforge_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Grant permissions to service role (backend uses service-role key)
GRANT ALL ON studyforge_chunks TO service_role;
GRANT USAGE ON SCHEMA public TO service_role;

-- ============================================================
-- RPC FUNCTIONS FOR VECTOR SEARCH AND SOURCE OPERATIONS
-- ============================================================

-- 1. Vector similarity search with optional metadata filters
-- Returns cosine distance (embedding <=> query_embedding) as DOUBLE PRECISION
-- Backend applies RELEVANCE_THRESHOLD = 0.60 on the returned distance
CREATE OR REPLACE FUNCTION studyforge_search_chunks(
    query_embedding VECTOR(1024),
    match_count INT DEFAULT 3,
    p_owner_user_id UUID DEFAULT NULL,
    p_source_kind TEXT DEFAULT NULL,
    p_grade SMALLINT DEFAULT NULL,
    p_source_id TEXT DEFAULT NULL,
    p_chapter_number SMALLINT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    source_id TEXT,
    chunk_index INT,
    content TEXT,
    distance DOUBLE PRECISION,
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
        (c.embedding <=> query_embedding) AS distance,
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
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- 2. Source listing/aggregation (replaces get_sources)
-- Returns unique sources with metadata aggregated from chunks
-- Aggregates distinct chapter/chapter_number values across all chunks per source
CREATE OR REPLACE FUNCTION studyforge_get_sources(
    p_owner_user_id UUID DEFAULT NULL,
    p_source_kind TEXT DEFAULT NULL
)
RETURNS TABLE (
    source_id TEXT,
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
    chapter TEXT[],
    chapter_number SMALLINT[],
    page_number SMALLINT[]
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        c.source_id,
        (ARRAY_AGG(c.source_name ORDER BY c.created_at))[1] AS source_name,
        (ARRAY_AGG(c.source_type ORDER BY c.created_at))[1] AS source_type,
        (ARRAY_AGG(c.source_kind ORDER BY c.created_at))[1] AS source_kind,
        (ARRAY_AGG(c.owner_user_id ORDER BY c.created_at))[1] AS owner_user_id,
        MAX(c.created_at) AS created_at,
        MAX(c.grade) AS grade,
        (ARRAY_AGG(c.subject ORDER BY c.created_at))[1] AS subject,
        (ARRAY_AGG(c.language ORDER BY c.created_at))[1] AS language,
        (ARRAY_AGG(c.book_series ORDER BY c.created_at))[1] AS book_series,
        (ARRAY_AGG(c.book_title ORDER BY c.created_at))[1] AS book_title,
        (ARRAY_AGG(c.part ORDER BY c.created_at))[1] AS part,
        (ARRAY_AGG(c.is_supplement ORDER BY c.created_at))[1] AS is_supplement,
        ARRAY_AGG(DISTINCT c.chapter) FILTER (WHERE c.chapter IS NOT NULL) AS chapter,
        ARRAY_AGG(DISTINCT c.chapter_number) FILTER (WHERE c.chapter_number IS NOT NULL) AS chapter_number,
        ARRAY_AGG(DISTINCT c.page_number) FILTER (WHERE c.page_number IS NOT NULL) AS page_number
    FROM studyforge_chunks c
    WHERE
        (p_owner_user_id IS NULL OR c.owner_user_id = p_owner_user_id)
        AND (p_source_kind IS NULL OR c.source_kind = p_source_kind)
    GROUP BY c.source_id
    ORDER BY MAX(c.created_at);
$$;

-- 3. Count chunks matching filter (for stats/debug)
CREATE OR REPLACE FUNCTION studyforge_count_chunks(
    p_owner_user_id UUID DEFAULT NULL,
    p_source_kind TEXT DEFAULT NULL,
    p_grade SMALLINT DEFAULT NULL,
    p_source_id TEXT DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE sql
STABLE
AS $$
    SELECT COUNT(*)
    FROM studyforge_chunks c
    WHERE
        (p_owner_user_id IS NULL OR c.owner_user_id = p_owner_user_id)
        AND (p_source_kind IS NULL OR c.source_kind = p_source_kind)
        AND (p_grade IS NULL OR c.grade = p_grade)
        AND (p_source_id IS NULL OR c.source_id = p_source_id);
$$;

-- 4. Delete source (all chunks for a source_id)
CREATE OR REPLACE FUNCTION studyforge_delete_source(
    p_source_id TEXT,
    p_owner_user_id UUID DEFAULT NULL
)
RETURNS VOID
LANGUAGE sql
AS $$
    DELETE FROM studyforge_chunks
    WHERE
        source_id = p_source_id
        AND (p_owner_user_id IS NULL OR owner_user_id = p_owner_user_id);
$$;

-- 5. Delete all chunks for a conversation/user (if needed for cleanup)
-- Not strictly needed but available
CREATE OR REPLACE FUNCTION studyforge_delete_user_chunks(
    p_owner_user_id UUID
)
RETURNS VOID
LANGUAGE sql
AS $$
    DELETE FROM studyforge_chunks
    WHERE owner_user_id = p_owner_user_id;
$$;

-- Grant execute permissions to service role
GRANT EXECUTE ON FUNCTION studyforge_search_chunks TO service_role;
GRANT EXECUTE ON FUNCTION studyforge_get_sources TO service_role;
GRANT EXECUTE ON FUNCTION studyforge_count_chunks TO service_role;
GRANT EXECUTE ON FUNCTION studyforge_delete_source TO service_role;
GRANT EXECUTE ON FUNCTION studyforge_delete_user_chunks TO service_role;

-- ============================================================
-- 6. Chunk-level document retrieval (replaces Chroma collection.get())
-- ============================================================
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
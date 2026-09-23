-- StudyForge AI — Phase 2.5D-2 Database Migration
-- Run this in Supabase SQL Editor

-- Create quiz_attempts table
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_id TEXT,
    title TEXT,
    score INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    percentage NUMERIC(5,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE quiz_attempts ENABLE ROW LEVEL SECURITY;

-- RLS Policies for quiz_attempts
-- Students can only SELECT their own quiz attempts
CREATE POLICY "Students can view own quiz attempts"
    ON quiz_attempts
    FOR SELECT
    USING (auth.uid() = user_id);

-- Students can only INSERT their own quiz attempts
CREATE POLICY "Students can create own quiz attempts"
    ON quiz_attempts
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Students can only UPDATE their own quiz attempts
CREATE POLICY "Students can update own quiz attempts"
    ON quiz_attempts
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Students can only DELETE their own quiz attempts
CREATE POLICY "Students can delete own quiz attempts"
    ON quiz_attempts
    FOR DELETE
    USING (auth.uid() = user_id);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_id ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_created_at ON quiz_attempts(created_at DESC);

-- Grant permissions to authenticated role
GRANT SELECT, INSERT, UPDATE, DELETE ON quiz_attempts TO authenticated;
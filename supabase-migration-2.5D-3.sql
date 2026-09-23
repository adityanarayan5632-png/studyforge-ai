-- StudyForge AI — Phase 2.5D-3 Database Migration
-- Run this in Supabase SQL Editor

-- Create study_activities table
CREATE TABLE IF NOT EXISTS study_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    activity_type TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE study_activities ENABLE ROW LEVEL SECURITY;

-- RLS Policies for study_activities
-- Students can only SELECT their own activities
CREATE POLICY "Students can view own study activities"
    ON study_activities
    FOR SELECT
    USING (auth.uid() = user_id);

-- Students can only INSERT their own activities
CREATE POLICY "Students can create own study activities"
    ON study_activities
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Students can only UPDATE their own activities
CREATE POLICY "Students can update own study activities"
    ON study_activities
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Students can only DELETE their own activities
CREATE POLICY "Students can delete own study activities"
    ON study_activities
    FOR DELETE
    USING (auth.uid() = user_id);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_study_activities_user_id ON study_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_study_activities_created_at ON study_activities(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_study_activities_activity_type ON study_activities(activity_type);

-- Grant permissions to authenticated role
GRANT SELECT, INSERT, UPDATE, DELETE ON study_activities TO authenticated;
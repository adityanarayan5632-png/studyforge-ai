-- StudyForge AI — Phase 2.5B Database Migration
-- Run this in Supabase SQL Editor

-- Create profiles table
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL,
  grade SMALLINT NOT NULL CHECK (grade BETWEEN 1 AND 5),
  board TEXT NOT NULL CHECK (board IN ('CBSE', 'Other')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- Students can only SELECT their own profile
CREATE POLICY "Students can view own profile"
  ON profiles
  FOR SELECT
  USING (auth.uid() = id);

-- Students can only INSERT their own profile (onboarding)
CREATE POLICY "Students can create own profile"
  ON profiles
  FOR INSERT
  WITH CHECK (auth.uid() = id);

-- Students can only UPDATE their own profile
CREATE POLICY "Students can update own profile"
  ON profiles
  FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Prevent DELETE (profiles are deleted via CASCADE when auth user is deleted)
-- No DELETE policy = no one can delete

-- Index for faster lookups (optional, auth.uid() is already unique)
CREATE INDEX IF NOT EXISTS idx_profiles_id ON profiles(id);

-- Grant permissions to authenticated role
GRANT SELECT, INSERT, UPDATE ON profiles TO authenticated;
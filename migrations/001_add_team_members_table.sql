-- Migration: Add team_members table and remove team_id from users

-- Step 1: Create team_members table
CREATE TABLE IF NOT EXISTS team_members (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL,
    user_id UUID NOT NULL,
    meta JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_del INTEGER DEFAULT 0,
    CONSTRAINT unique_team_user UNIQUE (team_id, user_id)
);

-- Step 2: Migrate existing team memberships from users table to team_members
-- (only if users table has team_id column)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'team_id'
    ) THEN
        -- Insert existing team memberships into team_members
        INSERT INTO team_members (team_id, user_id, created_at, updated_at, is_del)
        SELECT team_id, uuid, created_at, updated_at, is_del
        FROM users
        WHERE is_del = 0
        ON CONFLICT (team_id, user_id) DO NOTHING;

        -- Drop the team_id column from users
        ALTER TABLE users DROP COLUMN team_id;
    END IF;
END $$;

-- Step 3: Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id) WHERE is_del = 0;
CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON team_members(user_id) WHERE is_del = 0;

-- Step 4: Add comments
COMMENT ON TABLE team_members IS 'Junction table for many-to-many relationship between teams and users';
COMMENT ON COLUMN team_members.meta IS 'Additional metadata for the membership (e.g., role, permissions)';

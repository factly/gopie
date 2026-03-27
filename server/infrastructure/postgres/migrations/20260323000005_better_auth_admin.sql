-- +goose Up
-- +goose StatementBegin

-- Better Auth Admin Plugin Schema
-- https://www.better-auth.com/docs/plugins/admin#schema

-- Add admin plugin fields to user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user';
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS banned BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "banReason" TEXT;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "banExpires" TIMESTAMP WITH TIME ZONE;

-- Add impersonatedBy column to session table for admin impersonation
ALTER TABLE session ADD COLUMN IF NOT EXISTS "impersonatedBy" TEXT;

-- Index for role-based queries
CREATE INDEX IF NOT EXISTS idx_user_role ON "user"(role);
CREATE INDEX IF NOT EXISTS idx_user_banned ON "user"(banned);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Drop indexes
DROP INDEX IF EXISTS idx_user_banned;
DROP INDEX IF EXISTS idx_user_role;

-- Remove impersonatedBy column from session table
ALTER TABLE session DROP COLUMN IF EXISTS "impersonatedBy";

-- Remove admin plugin fields from user table
ALTER TABLE "user" DROP COLUMN IF EXISTS "banExpires";
ALTER TABLE "user" DROP COLUMN IF EXISTS "banReason";
ALTER TABLE "user" DROP COLUMN IF EXISTS banned;
ALTER TABLE "user" DROP COLUMN IF EXISTS role;

-- +goose StatementEnd

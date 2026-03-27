-- +goose Up
-- +goose StatementBegin

-- Drop old invitations schema
DROP INDEX IF EXISTS idx_invitations_expires_at;
DROP INDEX IF EXISTS idx_invitations_status;
DROP INDEX IF EXISTS idx_invitations_invitee_id;
DROP INDEX IF EXISTS idx_invitations_org_id;
DROP TABLE IF EXISTS invitations;
DROP TYPE IF EXISTS invitation_status;

-- Better Auth Core Schema
-- https://www.better-auth.com/docs/concepts/database#core-schema

CREATE TABLE IF NOT EXISTS "user" (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    "emailVerified" BOOLEAN NOT NULL DEFAULT FALSE,
    image TEXT,
    "twoFactorEnabled" BOOLEAN DEFAULT FALSE,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY,
    "userId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    "accountId" TEXT NOT NULL,
    "providerId" TEXT NOT NULL,
    "accessToken" TEXT,
    "refreshToken" TEXT,
    "accessTokenExpiresAt" TIMESTAMP WITH TIME ZONE,
    "refreshTokenExpiresAt" TIMESTAMP WITH TIME ZONE,
    scope TEXT,
    "idToken" TEXT,
    password TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verification (
    id TEXT PRIMARY KEY,
    identifier TEXT NOT NULL,
    value TEXT NOT NULL,
    "expiresAt" TIMESTAMP WITH TIME ZONE NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Better Auth Organization Plugin Schema
-- https://www.better-auth.com/docs/plugins/organization#schema

CREATE TABLE IF NOT EXISTS organization (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    logo TEXT,
    metadata TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session (
    id TEXT PRIMARY KEY,
    "userId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    "expiresAt" TIMESTAMP WITH TIME ZONE NOT NULL,
    "ipAddress" TEXT,
    "userAgent" TEXT,
    "activeOrganizationId" TEXT REFERENCES organization(id) ON DELETE SET NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS member (
    id TEXT PRIMARY KEY,
    "userId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    "organizationId" TEXT NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invitation (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    "inviterId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    "organizationId" TEXT NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    "expiresAt" TIMESTAMP WITH TIME ZONE NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Better Auth Two-Factor Plugin Schema
-- https://www.better-auth.com/docs/plugins/2fa#schema
CREATE TABLE IF NOT EXISTS "twoFactor" (
    id TEXT PRIMARY KEY,
    "userId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    secret TEXT,
    "backupCodes" TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for Better Auth Core
CREATE INDEX IF NOT EXISTS idx_user_email ON "user"(email);
CREATE INDEX IF NOT EXISTS idx_session_user_id ON session("userId");
CREATE INDEX IF NOT EXISTS idx_session_token ON session(token);
CREATE INDEX IF NOT EXISTS idx_account_user_id ON account("userId");
CREATE INDEX IF NOT EXISTS idx_account_provider ON account("providerId", "accountId");

-- Indexes for Better Auth Organization Plugin
CREATE INDEX IF NOT EXISTS idx_organization_slug ON organization(slug);
CREATE INDEX IF NOT EXISTS idx_member_user_id ON member("userId");
CREATE INDEX IF NOT EXISTS idx_member_organization_id ON member("organizationId");
CREATE INDEX IF NOT EXISTS idx_invitation_email ON invitation(email);
CREATE INDEX IF NOT EXISTS idx_invitation_organization_id ON invitation("organizationId");
CREATE INDEX IF NOT EXISTS idx_invitation_status ON invitation(status);
CREATE INDEX IF NOT EXISTS idx_two_factor_user_id ON "twoFactor"("userId");

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- Drop Better Auth Two-Factor Plugin indexes
DROP INDEX IF EXISTS idx_two_factor_user_id;

-- Drop Better Auth Organization Plugin indexes
DROP INDEX IF EXISTS idx_organization_role_org_id;
DROP INDEX IF EXISTS idx_invitation_status;
DROP INDEX IF EXISTS idx_invitation_organization_id;
DROP INDEX IF EXISTS idx_invitation_email;
DROP INDEX IF EXISTS idx_member_organization_id;
DROP INDEX IF EXISTS idx_member_user_id;
DROP INDEX IF EXISTS idx_organization_slug;

-- Drop Better Auth Core indexes
DROP INDEX IF EXISTS idx_account_provider;
DROP INDEX IF EXISTS idx_account_user_id;
DROP INDEX IF EXISTS idx_session_token;
DROP INDEX IF EXISTS idx_session_user_id;
DROP INDEX IF EXISTS idx_user_email;

-- Drop Better Auth Two-Factor Plugin tables
DROP TABLE IF EXISTS "twoFactor";

-- Drop Better Auth Organization Plugin tables
DROP TABLE IF EXISTS invitation;
DROP TABLE IF EXISTS member;
DROP TABLE IF EXISTS session;
DROP TABLE IF EXISTS organization;

-- Drop Better Auth Core tables
DROP TABLE IF EXISTS verification;
DROP TABLE IF EXISTS account;
DROP TABLE IF EXISTS "user";

-- Restore old invitations schema
CREATE TYPE invitation_status AS ENUM ('pending', 'accepted', 'declined', 'expired');

CREATE TABLE IF NOT EXISTS invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invitee_id TEXT NOT NULL,
    invited_by_user_id TEXT NOT NULL,
    status invitation_status NOT NULL DEFAULT 'pending',
    org_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
    UNIQUE(invitee_id, org_id, status)
);

CREATE INDEX idx_invitations_org_id ON invitations(org_id);
CREATE INDEX idx_invitations_invitee_id ON invitations(invitee_id);
CREATE INDEX idx_invitations_status ON invitations(status);
CREATE INDEX idx_invitations_expires_at ON invitations(expires_at);

-- +goose StatementEnd

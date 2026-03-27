package auth

import (
	"context"
	"errors"

	"github.com/factly/gopie/domain/models"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Repository provides direct PostgreSQL queries against Better Auth tables.
// These tables are managed by Better Auth (via the web app) and validated by the Go server.
type Repository struct {
	pool *pgxpool.Pool
}

func NewRepository(db any) *Repository {
	return &Repository{pool: db.(*pgxpool.Pool)}
}

// GetSessionByToken looks up a session by its token and checks it is not expired.
func (r *Repository) GetSessionByToken(ctx context.Context, token string) (*models.Session, error) {
	row := r.pool.QueryRow(ctx,
		`SELECT "id", "userId", "token", "expiresAt", "ipAddress", "userAgent", "activeOrganizationId", "createdAt", "updatedAt"
		 FROM "session"
		 WHERE "token" = $1 AND "expiresAt" > NOW()`,
		token,
	)

	var s models.Session
	err := row.Scan(
		&s.ID, &s.UserID, &s.Token, &s.ExpiresAt,
		&s.IPAddress, &s.UserAgent, &s.ActiveOrganizationID,
		&s.CreatedAt, &s.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &s, nil
}

// GetMemberByUserAndOrg returns the membership record for a user in an organization.
func (r *Repository) GetMemberByUserAndOrg(ctx context.Context, userID, orgID string) (*models.OrganizationMember, error) {
	row := r.pool.QueryRow(ctx,
		`SELECT "id", "userId", "organizationId", "role", "createdAt"
		 FROM "member"
		 WHERE "userId" = $1 AND "organizationId" = $2`,
		userID, orgID,
	)

	var m models.OrganizationMember
	err := row.Scan(&m.ID, &m.UserID, &m.OrganizationID, &m.Role, &m.CreatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &m, nil
}

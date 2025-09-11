package apikeys

import (
	"context"
	"errors"
	"time"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresAPIKeyStore) UpdateLastUsed(ctx context.Context, id, orgID string) (*models.APIKey, error) {
	uid, err := uuid.Parse(id)
	if err != nil {
		return nil, err
	}

	p, err := s.q.UpdateAPIKeyLastUsed(ctx, gen.UpdateAPIKeyLastUsedParams{
		ID:    pgtype.UUID{Bytes: uid, Valid: true},
		OrgID: orgID,
	})
	if err != nil {
		s.logger.Error("Error updating API key last used time", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrRecordNotFound
		}
		return nil, err
	}

	return &models.APIKey{
		ID:          p.ID.String(),
		Name:        p.Name,
		KeyHash:     p.KeyHash,
		CreatedBy:   p.CreatedBy,
		Description: p.Description.String,
		LastUsedAt:  &p.LastUsedAt.Time,
		ExpiresAt:   &p.ExpiresAt.Time,
		IsRevoked:   p.IsRevoked,
		OrgID:       p.OrgID,
		CreatedAt:   time.Time(p.CreatedAt.Time),
		UpdatedAt:   time.Time(p.UpdatedAt.Time),
	}, nil
}

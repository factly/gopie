package apikeys

import (
	"context"
	"errors"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresAPIKeyStore) Details(ctx context.Context, id, orgID string) (*models.APIKey, error) {
	uid, err := uuid.Parse(id)
	if err != nil {
		return nil, err
	}

	p, err := s.q.GetAPIKey(ctx, gen.GetAPIKeyParams{
		ID:    pgtype.UUID{Bytes: uid, Valid: true},
		OrgID: orgID,
	})
	if err != nil {
		s.logger.Error("Error fetching API key", zap.Error(err))
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
		CreatedAt:   p.CreatedAt.Time,
		UpdatedAt:   p.UpdatedAt.Time,
	}, nil
}

func (s *PostgresAPIKeyStore) GetByHash(ctx context.Context, keyHash string) (*models.APIKey, error) {
	p, err := s.q.GetAPIKeyByHash(ctx, keyHash)
	if err != nil {
		s.logger.Error("Error fetching API key by hash", zap.Error(err))
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
		CreatedAt:   p.CreatedAt.Time,
		UpdatedAt:   p.UpdatedAt.Time,
	}, nil
}

package apikeys

import (
	"context"
	"errors"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/jackc/pgx/v5"
	"go.uber.org/zap"
)

func (s *PostgresAPIKeyStore) GetByHash(ctx context.Context, keyHash string) (*models.APIKey, error) {
	p, err := s.q.GetAPIKeyByHash(ctx, keyHash)
	if err != nil {
		s.logger.Error("Error fetching API key by hash", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrRecordNotFound
		}
		return nil, err
	}

	apiKey := &models.APIKey{
		ID:          p.ID.String(),
		Name:        p.Name,
		KeyHash:     p.KeyHash,
		CreatedBy:   p.CreatedBy,
		Description: p.Description.String,
		IsRevoked:   p.IsRevoked,
		CreatedAt:   p.CreatedAt.Time,
		UpdatedAt:   p.UpdatedAt.Time,
	}
	if p.LastUsedAt.Valid {
		apiKey.LastUsedAt = &p.LastUsedAt.Time
	}
	if p.ExpiresAt.Valid {
		apiKey.ExpiresAt = &p.ExpiresAt.Time
	}
	return apiKey, nil
}

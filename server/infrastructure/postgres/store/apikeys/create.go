package apikeys

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresAPIKeyStore) Create(ctx context.Context, params models.CreateAPIKeyParams) (*models.APIKeyResponse, error) {
	var expiresAt pgtype.Timestamptz
	if params.ExpiresAt != nil {
		expiresAt = pgtype.Timestamptz{
			Time:  *params.ExpiresAt,
			Valid: true,
		}
	}

	p, err := s.q.CreateAPIKey(ctx, gen.CreateAPIKeyParams{
		Name:        params.Name,
		KeyHash:     params.KeyHash,
		CreatedBy:   params.CreatedBy,
		Description: pgtype.Text{String: params.Description, Valid: params.Description != ""},
		ExpiresAt:   expiresAt,
	})
	if err != nil {
		s.logger.Critical("Error creating API key", zap.Error(err))
		return nil, err
	}

	apiKey := models.APIKey{
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

	return &models.APIKeyResponse{
		APIKey: apiKey,
	}, nil
}

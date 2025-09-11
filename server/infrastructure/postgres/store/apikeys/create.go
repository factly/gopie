package apikeys

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresAPIKeyStore) Create(ctx context.Context, params models.CreateAPIKeyParams) (*models.APIKeyResponse, error) {
	// Parse application ID

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
		OrgID:       params.OrgID,
	})
	if err != nil {
		s.logger.Error("Error creating API key", zap.Error(err))
		return nil, err
	}

	apiKey := models.APIKey{
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
	}

	return &models.APIKeyResponse{
		APIKey: apiKey,
	}, nil
}

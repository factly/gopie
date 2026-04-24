package apikeys

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"go.uber.org/zap"
)

func (s *PostgresAPIKeyStore) SearchAPIKeys(ctx context.Context, query string, pagination models.Pagination) (*models.PaginationView[*models.APIKey], error) {
	apiKeys, err := s.q.SearchAPIKeys(ctx, gen.SearchAPIKeysParams{
		Column1: query,
		Limit:   int32(pagination.Limit),
		Offset:  int32(pagination.Offset),
	})
	if err != nil {
		s.logger.Error("Error searching API keys", zap.Error(err))
		return nil, err
	}

	var items []*models.APIKey
	for _, p := range apiKeys {
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
		items = append(items, apiKey)
	}

	count, err := s.q.GetAPIKeysCount(ctx)
	if err != nil {
		s.logger.Error("Error getting API keys count", zap.Error(err))
		return nil, err
	}

	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, int(count), items)
	return &paginationView, nil
}

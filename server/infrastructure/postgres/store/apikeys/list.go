package apikeys

import (
	"context"
	"time"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"go.uber.org/zap"
)

func (s *PostgresAPIKeyStore) ListExpiredAPIKeys(ctx context.Context, pagination models.Pagination, orgID string) (*models.PaginationView[*models.APIKey], error) {
	apiKeys, err := s.q.ListExpiredAPIKeys(ctx, gen.ListExpiredAPIKeysParams{
		OrgID:  orgID,
		Limit:  int32(pagination.Limit),
		Offset: int32(pagination.Offset),
	})
	if err != nil {
		s.logger.Error("Error listing expired API keys", zap.Error(err))
		return nil, err
	}

	var items []*models.APIKey
	for _, p := range apiKeys {
		items = append(items, &models.APIKey{
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
		})
	}

	// For expired keys, we just use the length of returned items as total count
	// since we don't need pagination for this use case
	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, len(items), items)
	return &paginationView, nil
}

func (s *PostgresAPIKeyStore) SearchAPIKeys(ctx context.Context, query string, pagination models.Pagination, orgID string) (*models.PaginationView[*models.APIKey], error) {
	apiKeys, err := s.q.SearchAPIKeys(ctx, gen.SearchAPIKeysParams{
		OrgID:   orgID,
		Column2: query,
		Limit:   int32(pagination.Limit),
		Offset:  int32(pagination.Offset),
	})
	if err != nil {
		s.logger.Error("Error searching API keys", zap.Error(err))
		return nil, err
	}

	var items []*models.APIKey
	for _, p := range apiKeys {
		items = append(items, &models.APIKey{
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
		})
	}

	count, err := s.q.GetAPIKeysCount(ctx, orgID)
	if err != nil {
		s.logger.Error("Error getting API keys count", zap.Error(err))
		return nil, err
	}

	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, int(count), items)
	return &paginationView, nil
}

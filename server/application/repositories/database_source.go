package repositories

import (
	"context"

	"github.com/factly/gopie/domain/models"
)

// DatabaseSourceStoreRepository defines interface for database source repository
type DatabaseSourceStoreRepository interface {
	Create(ctx context.Context, params models.CreateDatabaseSourceParams) (*models.DatabaseSource, error)
	Get(ctx context.Context, datasetID string, orgID string) (*models.DatabaseSource, error)
	Delete(ctx context.Context, id string) error
	List(ctx context.Context, limit, offset int, orgID string) ([]*models.DatabaseSource, error)
	UpdateLastUpdatedAt(ctx context.Context, params models.UpdateDatabaseSourceLastUpdatedAtParams) error
	HasTimestampColumn(ctx context.Context, datasetID, orgID string) (bool, error)
}

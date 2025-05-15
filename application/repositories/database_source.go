package repositories

import (
	"context"

	"github.com/factly/gopie/domain/models"
)

// DatabaseSourceStoreRepository defines interface for database source repository
type DatabaseSourceStoreRepository interface {
	Create(ctx context.Context, params models.CreateDatabaseSourceParams) (*models.DatabaseSource, error)
	Get(ctx context.Context, id string) (*models.DatabaseSource, error)
	Delete(ctx context.Context, id string) error
	List(ctx context.Context, limit, offset int) ([]*models.DatabaseSource, error)
}

package repositories

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/config"
)

type StoreRepository interface {
	Connect(cfg *config.PostgresConfig) error
	Close() error
	GetDB() interface{}
}

type ProjectStoreRepository interface {
	Create(ctx context.Context, params models.CreateProjectParams) (*models.Project, error)
	Delete(ctx context.Context, id string) error
	Details(ctx context.Context, id string) (*models.Project, error)
	Update(ctx context.Context, projectID string, params *models.UpdateProjectParams) (*models.Project, error)
	SearchProject(ctx context.Context, query string, pagination models.Pagination) (*models.PaginationView[*models.SearchProjectsResults], error)
}

type DatasetStoreRepository interface {
	Create(ctx context.Context, params *models.CreateDatasetParams) (*models.Dataset, error)
	Delete(ctx context.Context, id string) error
	Details(ctx context.Context, id string) (*models.Dataset, error)
	List(ctx context.Context, projectID string, pagination models.Pagination) (*models.PaginationView[*models.Dataset], error)
	Update(ctx context.Context, datasetID string, params *models.UpdateDatasetParams) (*models.Dataset, error)
	GetByTableName(ctx context.Context, tableName string) (*models.Dataset, error)

	CreateFailedUpload(ctx context.Context, datasetID string, errorMsg string) (*models.FailedDatasetUpload, error)
	DeleteFailedUploadsByDatasetID(ctx context.Context, datasetID string) error
	ListFailedUploads(ctx context.Context) ([]*models.FailedDatasetUpload, error)
}

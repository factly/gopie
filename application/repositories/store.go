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
	ListProjectDatasets(ctx context.Context, id string, pagination models.Pagination) (*models.PaginationView[*models.ListProjectDatasetsResults], error)
	List(ctx context.Context, pagination models.Pagination) (*models.PaginationView[*models.Project], error)
	Update(ctx context.Context, projectID string, params *models.UpdateProjectParams) (*models.Project, error)
	SearchProject(ctx context.Context, query string, pagination models.Pagination) (*models.PaginationView[*models.SearchProjectsResults], error)
}

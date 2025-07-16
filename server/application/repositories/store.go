package repositories

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/config"
)

type StoreRepository interface {
	Connect(cfg *config.PostgresConfig) error
	Close() error
	GetDB() any
}

type ProjectStoreRepository interface {
	Create(ctx context.Context, params models.CreateProjectParams) (*models.Project, error)
	Delete(ctx context.Context, id string, orgID string) error
	Details(ctx context.Context, id string, orgID string) (*models.Project, error)
	Update(ctx context.Context, projectID string, params *models.UpdateProjectParams) (*models.Project, error)
	SearchProject(ctx context.Context, query string, pagination models.Pagination, orgID string) (*models.PaginationView[*models.SearchProjectsResults], error)
	GetProjectByID(ctx context.Context, datasetID string) (*models.Project, error)
	ListAllProjects(ctx context.Context) ([]*models.Project, error)
}

type DatasetStoreRepository interface {
	Create(ctx context.Context, params *models.CreateDatasetParams) (*models.Dataset, error)
	Delete(ctx context.Context, id string, orgID string) error
	Details(ctx context.Context, id string, orgID string) (*models.Dataset, error)
	List(ctx context.Context, projectID string, pagination models.Pagination) (*models.PaginationView[*models.Dataset], error)
	Update(ctx context.Context, datasetID string, params *models.UpdateDatasetParams) (*models.Dataset, error)
	GetByTableName(ctx context.Context, tableName string, orgID string) (*models.Dataset, error)
	GetDatasetByID(ctx context.Context, datasetID string) (*models.Dataset, error)

	CreateFailedUpload(ctx context.Context, datasetID string, errorMsg string) (*models.FailedDatasetUpload, error)
	DeleteFailedUploadsByDatasetID(ctx context.Context, datasetID string) error
	ListFailedUploads(ctx context.Context) ([]*models.FailedDatasetUpload, error)

	CreateDatasetSummary(ctx context.Context, datasetName string, summary *[]models.DatasetSummary) (*models.DatasetSummaryWithName, error)
	DeleteDatasetSummary(ctx context.Context, datasetName string) error
	GetDatasetSummary(ctx context.Context, datasetName string) (*models.DatasetSummaryWithName, error)
	ListAllDatasets(ctx context.Context) ([]*models.Dataset, error)
}

type ChatStoreRepository interface {
	CreateChat(ctx context.Context, params *models.CreateChatParams) (*models.ChatWithMessages, error)
	DeleteChat(ctx context.Context, id, createdBy, orgID string) error
	ListUserChats(ctx context.Context, userID, orgID string, pagination models.Pagination) (*models.PaginationView[*models.Chat], error)
	UpdateChat(ctx context.Context, chatID string, params *models.UpdateChatParams) (*models.Chat, error)
	GetChatByID(ctx context.Context, chatID string) (*models.Chat, error)
	UpdateChatVisibility(ctx context.Context, chatID, userID string, params *models.UpdateChatVisibilityParams) (*models.Chat, error)

	GetChatMessages(ctx context.Context, chatID string) ([]*models.ChatMessage, error)
	AddNewMessage(ctx context.Context, chatID string, messages []models.ChatMessage) ([]models.ChatMessage, error)
}

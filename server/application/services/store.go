package services

import (
	"context"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type ProjectService struct {
	projectRepo repositories.ProjectStoreRepository
}

func NewProjectService(projectRepo repositories.ProjectStoreRepository) *ProjectService {
	return &ProjectService{
		projectRepo: projectRepo,
	}
}

// Create - Create project
func (service *ProjectService) Create(params models.CreateProjectParams) (*models.Project, error) {
	return service.projectRepo.Create(context.Background(), params)
}

// Details - Get project by id
func (service *ProjectService) Details(id, orgID, createdBy string) (*models.Project, error) {
	return service.projectRepo.Details(context.Background(), id, orgID)
}

func (service *ProjectService) GetProjectByID(id string) (*models.Project, error) {
	return service.projectRepo.GetProjectByID(context.Background(), id)
}

// Update - Update project
func (service *ProjectService) Update(projectID string, role models.Role, params *models.UpdateProjectParams) (*models.Project, error) {
	if role == models.Admin {
		return service.projectRepo.Update(context.Background(), projectID, params)
	}
	return service.projectRepo.UpdateByOrgAndCreator(context.Background(), projectID, params.OrgID, params.UpdatedBy, params)
}

// Delete - Delete project
func (service *ProjectService) Delete(id, orgID, createdBy string, role models.Role) error {
	if role == models.Admin {
		return service.projectRepo.Delete(context.Background(), id, orgID)
	}
	return service.projectRepo.DeleteByOrgAndCreator(context.Background(), id, orgID, createdBy)
}

func (service *ProjectService) ProjectsBelongToOrg(projectIDs []string, orgID string) (bool, error) {
	return service.projectRepo.ProjectsBelongToOrg(context.Background(), projectIDs, orgID)
}

func (service *ProjectService) DatasetsBelongToOrg(datasetNames []string, orgID string) (bool, error) {
	return service.projectRepo.DatasetsBelongToOrg(context.Background(), datasetNames, orgID)
}

// List - Search projects
func (service *ProjectService) List(query string, limit, page int, orgID, createdBy string) (*models.PaginationView[*models.SearchProjectsResults], error) {
	pagination := models.NewPagination()
	if limit != 0 {
		pagination.Limit = limit
	}
	pagination.Offset = (page - 1) * limit

	return service.projectRepo.SearchProjectByOrgAndCreator(context.Background(), query, pagination, orgID, createdBy)
}

func (service *ProjectService) ListAllProjects() ([]*models.Project, error) {
	return service.projectRepo.ListAllProjects(context.Background())
}

type DatasetService struct {
	datasetRepo repositories.DatasetStoreRepository
}

func NewDatasetService(datasetRepo repositories.DatasetStoreRepository) *DatasetService {
	return &DatasetService{
		datasetRepo: datasetRepo,
	}
}

func (service *DatasetService) GetDB() *pgxpool.Pool {
	return service.datasetRepo.GetDB().(*pgxpool.Pool)
}

func (service *DatasetService) Create(params *models.CreateDatasetParams) (*models.Dataset, error) {
	return service.datasetRepo.Create(context.Background(), params)
}

func (service *DatasetService) Details(id, orgID, createdBy string) (*models.Dataset, error) {
	return service.datasetRepo.DetailsByOrgAndCreator(context.Background(), id, orgID, createdBy)
}

func (service *DatasetService) GetByTableName(tableName string, orgID string) (*models.Dataset, error) {
	return service.datasetRepo.GetByTableName(context.Background(), tableName, orgID)
}

func (service *DatasetService) List(projectID string, role models.Role, orgID, createdBy string, limit, page int) (*models.PaginationView[*models.Dataset], error) {
	pagination := models.NewPagination()
	if limit != 0 {
		pagination.Limit = limit
	}
	pagination.Offset = (page - 1) * limit
	return service.datasetRepo.ListByProjectAndOrg(context.Background(), projectID, orgID, createdBy, pagination)
}

func (service *DatasetService) Delete(id, orgID, createdBy string, role models.Role) error {
	if role == models.Admin {
		return service.datasetRepo.Delete(context.Background(), id, orgID)
	}
	return service.datasetRepo.DeleteByOrgAndCreator(context.Background(), id, orgID, createdBy)
}

func (service *DatasetService) Update(id string, role models.Role, params *models.UpdateDatasetParams) (*models.Dataset, error) {
	if role == models.Admin {
		return service.datasetRepo.Update(context.Background(), id, params)
	}
	return service.datasetRepo.UpdateByOrgAndCreator(context.Background(), id, params.OrgID, params.UpdatedBy, params)
}

func (service *DatasetService) UpdateWithTx(tx pgx.Tx, id string, params *models.UpdateDatasetParams) (*models.Dataset, error) {
	return service.datasetRepo.UpdateWithTx(context.Background(), tx, id, params)
}

func (services *DatasetService) CreateFailedUpload(datasetID, errorMsg string) (*models.FailedDatasetUpload, error) {
	return services.datasetRepo.CreateFailedUpload(context.Background(), datasetID, errorMsg)
}

func (services *DatasetService) ListFailedUploads() ([]*models.FailedDatasetUpload, error) {
	return services.datasetRepo.ListFailedUploads(context.Background())
}

func (services *DatasetService) DeleteFailedUploadsByDatasetID(datasetID string) error {
	return services.datasetRepo.DeleteFailedUploadsByDatasetID(context.Background(), datasetID)
}

func (services *DatasetService) CreateDatasetSummary(datasetName string, summary *[]models.DatasetSummary) (*models.DatasetSummaryWithName, error) {
	return services.datasetRepo.CreateDatasetSummary(context.Background(), datasetName, summary)
}

func (services *DatasetService) CreateSummaryWithTx(tx pgx.Tx, datasetName string, datasetSummary *[]models.DatasetSummary) (*models.DatasetSummaryWithName, error) {
	return services.datasetRepo.CreateSummaryWithTx(context.Background(), tx, datasetName, datasetSummary)
}

func (services *DatasetService) DeleteDatasetSummary(datasetName string) error {
	return services.datasetRepo.DeleteDatasetSummary(context.Background(), datasetName)
}

func (services *DatasetService) DeleteSummaryWithTx(tx pgx.Tx, datasetName string) error {
	return services.datasetRepo.DeleteSummaryWithTx(context.Background(), tx, datasetName)
}

func (services *DatasetService) GetDatasetSummary(datasetName string) (*models.DatasetSummaryWithName, error) {
	return services.datasetRepo.GetDatasetSummary(context.Background(), datasetName)
}

func (services *DatasetService) GetDatasetByID(datasetID string) (*models.Dataset, error) {
	return services.datasetRepo.GetDatasetByID(context.Background(), datasetID)
}

func (service *DatasetService) ListAllDatasets() ([]*models.Dataset, error) {
	return service.datasetRepo.ListAllDatasets(context.Background())
}

func (service *DatasetService) ListALlDatasetsFromProject(projectID string) ([]*models.Dataset, error) {
	return service.datasetRepo.ListALlDatasetsFromProject(context.Background(), projectID)
}

func (service *DatasetService) GetProjectForDataset(datasetID string) (string, error) {
	return service.datasetRepo.GetProjectForDataset(context.Background(), datasetID)
}

// GetDatasetsByIDs fetches multiple datasets by their IDs for a given organization
func (s *DatasetService) GetDatasetsByIDs(ctx context.Context, datasetIDs []string, orgID string) ([]*models.Dataset, error) {
	return s.datasetRepo.GetDatasetsByIDs(ctx, datasetIDs, orgID)
}

// GetProjectsByIDs - Get projects by IDs
func (service *ProjectService) GetProjectsByIDs(ctx context.Context, projectIDs []string, orgID string) ([]*models.Project, error) {
	return service.projectRepo.GetProjectsByIDs(ctx, projectIDs, orgID)
}

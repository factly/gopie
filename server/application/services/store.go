package services

import (
	"context"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
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
func (service *ProjectService) Details(id, orgID string) (*models.Project, error) {
	return service.projectRepo.Details(context.Background(), id, orgID)
}

func (service *ProjectService) GetProjectByID(id string) (*models.Project, error) {
	return service.projectRepo.GetProjectByID(context.Background(), id)
}

// Update - Update project
func (service *ProjectService) Update(projectID string, params *models.UpdateProjectParams) (*models.Project, error) {
	return service.projectRepo.Update(context.Background(), projectID, params)
}

// Delete - Delete project
func (service *ProjectService) Delete(id, orgID string) error {
	return service.projectRepo.Delete(context.Background(), id, orgID)
}

// List - Search projects
func (service *ProjectService) List(query string, limit, offset int, orgID string) (*models.PaginationView[*models.SearchProjectsResults], error) {
	pagination := models.NewPagination()
	if limit != 0 {
		pagination.Limit = limit
	}
	return service.projectRepo.SearchProject(context.Background(), query, pagination, orgID)
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

func (service *DatasetService) Create(params *models.CreateDatasetParams) (*models.Dataset, error) {
	return service.datasetRepo.Create(context.Background(), params)
}

func (service *DatasetService) Details(id string, orgID string) (*models.Dataset, error) {
	return service.datasetRepo.Details(context.Background(), id, orgID)
}

func (service *DatasetService) GetByTableName(tableName string, orgID string) (*models.Dataset, error) {
	return service.datasetRepo.GetByTableName(context.Background(), tableName, orgID)
}

func (service *DatasetService) List(projectID string, limit, page int) (*models.PaginationView[*models.Dataset], error) {
	pagination := models.NewPagination()
	if limit != 0 {
		pagination.Limit = limit
	}
	pagination.Offset = (page - 1) * limit
	return service.datasetRepo.List(context.Background(), projectID, pagination)
}

func (service *DatasetService) Delete(id string, orgID string) error {
	return service.datasetRepo.Delete(context.Background(), id, orgID)
}

func (service *DatasetService) Update(id string, params *models.UpdateDatasetParams) (*models.Dataset, error) {
	return service.datasetRepo.Update(context.Background(), id, params)
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

func (services *DatasetService) DeleteDatasetSummary(datasetName string) error {
	return services.datasetRepo.DeleteDatasetSummary(context.Background(), datasetName)
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

func (service *DatasetService) ListALlDatasestFromProject(projectID string) ([]*models.Dataset, error) {
	return service.datasetRepo.ListALlDatasestFromProject(context.Background(), projectID)
}

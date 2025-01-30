package services

import (
	"context"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
)

type ProjectService struct {
	ProjectRepo repositories.ProjectStoreRepository
}

func NewProjectService(projectRepo repositories.ProjectStoreRepository) *ProjectService {
	return &ProjectService{
		ProjectRepo: projectRepo,
	}
}

// Create - Create project
func (service *ProjectService) Create(params models.CreateProjectParams) (*models.Project, error) {
	return service.ProjectRepo.Create(context.Background(), params)
}

// Details - Get project by id
func (service *ProjectService) Details(id string) (*models.Project, error) {
	return service.ProjectRepo.Details(context.Background(), id)
}

// Update - Update project
func (service *ProjectService) Update(projectID string, params *models.UpdateProjectParams) (*models.Project, error) {
	return service.ProjectRepo.Update(context.Background(), projectID, params)
}

// Delete - Delete project
func (service *ProjectService) Delete(id string) error {
	return service.ProjectRepo.Delete(context.Background(), id)
}

// List - List projects
func (service *ProjectService) List(limit, offset int) (*models.PaginationView[*models.Project], error) {
	pagination := models.NewPagination()
	if limit != 0 {
		pagination.Limit = limit
	}
	return service.ProjectRepo.List(context.Background(), pagination)
}

// SearchProjects - Search projects
func (service *ProjectService) SearchProjects(query string, limit, offset int) (*models.PaginationView[*models.SearchProjectsResults], error) {
	pagination := models.NewPagination()
	if limit != 0 {
		pagination.Limit = limit
	}
	return service.ProjectRepo.SearchProject(context.Background(), query, pagination)
}

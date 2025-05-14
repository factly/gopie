package services

import (
	"context"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/logger"
	"go.uber.org/zap"
)

// DatabaseSourceService handles database source operations
type DatabaseSourceService struct {
	dbSourceRepo repositories.DatabaseSourceStoreRepository
	logger       *logger.Logger
}

// NewDatabaseSourceService creates a new database source service
func NewDatabaseSourceService(dbSourceRepo repositories.DatabaseSourceStoreRepository, logger *logger.Logger) *DatabaseSourceService {
	return &DatabaseSourceService{
		dbSourceRepo: dbSourceRepo,
		logger:       logger,
	}
}

// Create creates a new database source
func (s *DatabaseSourceService) Create(params *models.CreateDatabaseSourceParams) (*models.DatabaseSource, error) {
	s.logger.Info("Creating database source", zap.String("project_id", params.ProjectID))
	return s.dbSourceRepo.Create(context.Background(), *params)
}

// Get retrieves a database source by ID
func (s *DatabaseSourceService) Get(id string) (*models.DatabaseSource, error) {
	s.logger.Info("Getting database source", zap.String("id", id))
	return s.dbSourceRepo.Get(context.Background(), id)
}

// Update updates a database source
func (s *DatabaseSourceService) Update(params *models.UpdateDatabaseSourceParams) (*models.DatabaseSource, error) {
	s.logger.Info("Updating database source", zap.String("id", params.ID))
	return s.dbSourceRepo.Update(context.Background(), *params)
}

// Delete deletes a database source
func (s *DatabaseSourceService) Delete(id string) error {
	s.logger.Info("Deleting database source", zap.String("id", id))
	return s.dbSourceRepo.Delete(context.Background(), id)
}

// List lists all database sources
func (s *DatabaseSourceService) List(limit, offset int) ([]*models.DatabaseSource, error) {
	s.logger.Info("Listing database sources", zap.Int("limit", limit), zap.Int("offset", offset))
	return s.dbSourceRepo.List(context.Background(), limit, offset)
}

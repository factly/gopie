package services

import (
	"context"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/logger"
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
	return s.dbSourceRepo.Create(context.Background(), *params)
}

// Get retrieves a database source by ID
func (s *DatabaseSourceService) Get(id string) (*models.DatabaseSource, error) {
	return s.dbSourceRepo.Get(context.Background(), id)
}

// Delete deletes a database source
func (s *DatabaseSourceService) Delete(id string) error {
	return s.dbSourceRepo.Delete(context.Background(), id)
}

// List lists all database sources
func (s *DatabaseSourceService) List(limit, offset int) ([]*models.DatabaseSource, error) {
	return s.dbSourceRepo.List(context.Background(), limit, offset)
}

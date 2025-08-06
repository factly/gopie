package services

import (
	"io"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/logger"
)

type downloadService struct {
	repo   repositories.DownloadRepository
	logger *logger.Logger
}

func NewDownloadService(repo repositories.DownloadRepository, logger *logger.Logger) *downloadService {
	return &downloadService{
		repo:   repo,
		logger: logger,
	}
}

func (s *downloadService) CreateAndStream(req *models.CreateDownloadRequest) (io.ReadCloser, error) {
	return s.repo.CreateAndStream(req)
}

func (s *downloadService) List(userID, orgID string, limit, offset int) ([]models.Download, error) {
	return s.repo.List(userID, orgID, limit, offset)
}

func (s *downloadService) Get(downloadID, userID, orgID string) (*models.Download, error) {
	return s.repo.Get(downloadID, userID, orgID)
}

func (s *downloadService) Delete(downloadID, userID, orgID string) error {
	return s.repo.Delete(downloadID, userID, orgID)
}

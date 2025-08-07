package services

import (
	"io"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/logger"
)

type DownloadService struct {
	repo   repositories.DownloadRepository
	logger *logger.Logger
}

func NewDownloadService(repo repositories.DownloadRepository, logger *logger.Logger) *DownloadService {
	return &DownloadService{
		repo:   repo,
		logger: logger,
	}
}

func (s *DownloadService) CreateAndStream(req *models.CreateDownloadRequest) (io.ReadCloser, error) {
	return s.repo.CreateAndStream(req)
}

func (s *DownloadService) List(userID, orgID string, limit, offset int) ([]models.Download, error) {
	return s.repo.List(userID, orgID, limit, offset)
}

func (s *DownloadService) Get(downloadID, userID, orgID string) (*models.Download, error) {
	return s.repo.Get(downloadID, userID, orgID)
}

func (s *DownloadService) Delete(downloadID, userID, orgID string) error {
	return s.repo.Delete(downloadID, userID, orgID)
}

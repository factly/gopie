package services

import (
	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/logger"
)

type DownloadServerService struct {
	repo   repositories.DownloadRepository
	logger *logger.Logger
}

func NewDownloadServerService(repo repositories.DownloadRepository, logger *logger.Logger) *DownloadServerService {
	return &DownloadServerService{
		repo:   repo,
		logger: logger,
	}
}

func (s *DownloadServerService) CreateAndStream(req *models.CreateDownloadRequest) (<-chan models.DownloadsSSEData, error) {
	return s.repo.CreateAndStream(req)
}

func (s *DownloadServerService) List(userID, orgID string, limit, offset int) ([]models.Download, error) {
	return s.repo.List(userID, orgID, limit, offset)
}

func (s *DownloadServerService) Get(downloadID, userID, orgID string) (*models.Download, error) {
	return s.repo.Get(downloadID, userID, orgID)
}

func (s *DownloadServerService) Delete(downloadID, userID, orgID string) error {
	return s.repo.Delete(downloadID, userID, orgID)
}

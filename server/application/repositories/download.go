package repositories

import (
	"github.com/factly/gopie/domain/models"
)

type DownloadRepository interface {
	CreateAndStream(req *models.CreateDownloadRequest) (<-chan models.DownloadsSSEData, error)
	List(userID, orgID string, limit, offset int) ([]models.Download, error)
	Get(downloadID, userID, orgID string) (*models.Download, error)
	Delete(downloadID, userID, orgID string) error
}

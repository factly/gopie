package repositories

import (
	"io"

	"github.com/factly/gopie/domain/models"
)

type DownloadRepository interface {
	CreateAndStream(req *models.CreateDownloadRequest) (io.ReadCloser, error)
	List(userID, orgID string, limit, offset int) ([]models.Download, error)
	Get(downloadID, userID, orgID string) (*models.Download, error)
	Delete(downloadID, userID, orgID string) error
}

package download

import (
	"net/http"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/config"
)

type downloadRepository struct {
	client  *http.Client
	baseURL string
}

func NewDownloadRepository(cfg *config.DownloadsServerConfig) repositories.DownloadRepository {
	return &downloadRepository{
		client:  &http.Client{},
		baseURL: cfg.Url,
	}
}

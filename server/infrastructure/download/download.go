package download

import (
	"net/http"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg/config"
)

type downloadServerRepository struct {
	client  *http.Client
	baseURL string
}

func NewDownloadServerRepository(cfg *config.DownloadsServerConfig) repositories.DownloadServerRepository {
	return &downloadServerRepository{
		client:  &http.Client{},
		baseURL: cfg.Url,
	}
}

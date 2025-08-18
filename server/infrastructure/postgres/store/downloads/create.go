package downloads

import (
	"context"

	"github.com/factly/gopie/domain/models"
)

func (s *PgDownloadsStore) CreateDownload(ctx context.Context, req *models.CreateDownloadRequest) (*models.Download, error) {
	genParams := req.ToGenCreateDownloadParams()

	genDownload, err := s.q.CreateDownload(ctx, genParams)
	if err != nil {
		return nil, err
	}

	return models.FromGenDownload(genDownload), nil
}

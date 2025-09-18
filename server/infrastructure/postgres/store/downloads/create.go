package downloads

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"go.uber.org/zap"
)

func (s *PgDownloadsStore) CreateDownload(ctx context.Context, req *models.CreateDownloadRequest) (*models.Download, error) {
	genParams := req.ToGenCreateDownloadParams()

	genDownload, err := s.q.CreateDownload(ctx, genParams)
	if err != nil {
		s.logger.Critical("Error creating download", zap.Error(err))
		return nil, err
	}

	return models.FromGenDownload(genDownload), nil
}

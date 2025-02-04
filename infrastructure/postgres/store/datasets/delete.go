package datasets

import (
	"context"
	"errors"

	"github.com/factly/gopie/domain"
	"github.com/jackc/pgx/v5"
	"go.uber.org/zap"
)

func (s *PgDatasetStore) Delete(ctx context.Context, datasetID string) error {
	err := s.q.DeleteDataset(ctx, datasetID)
	if err != nil {
		s.logger.Error("Error deleting dataset", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return domain.ErrRecordNotFound
		}
		return err
	}
	return nil
}

func (s *PgDatasetStore) DeleteFailedUploadsByDatasetID(ctx context.Context, datasetID string) error {
	err := s.q.DeleteFailedDatasetUpload(ctx, datasetID)
	if err != nil {
		s.logger.Error("Error deleting failed uploads", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return domain.ErrRecordNotFound
		}
		return err
	}
	return nil
}

package datasets

import (
	"context"
	"errors"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PgDatasetStore) Delete(ctx context.Context, datasetID string, orgID string) error {
	err := s.q.DeleteDataset(ctx, gen.DeleteDatasetParams{
		ID:    datasetID,
		OrgID: pgtype.Text{String: orgID, Valid: true},
	})
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

func (s *PgDatasetStore) DeleteDatasetSummary(ctx context.Context, datasetName string) error {
	err := s.q.DeleteDatasetSummary(ctx, datasetName)
	if err != nil {
		s.logger.Error("Error deleting dataset summary", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return domain.ErrRecordNotFound
		}
		return err
	}
	return nil
}

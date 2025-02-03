package datasets

import (
	"context"
	"encoding/json"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PgDatasetStore) Update(ctx context.Context, datasetID string, updateDatasetParams *models.UpdateDatasetParams) (*models.Dataset, error) {
	columns, err := json.Marshal(updateDatasetParams.Columns)
	if err != nil {
		s.logger.Error("Error marshaling columns", zap.Error(err))
		return nil, err
	}
	d, err := s.q.UpdateDataset(ctx, gen.UpdateDatasetParams{
		ID:          datasetID,
		Description: pgtype.Text{String: updateDatasetParams.Description, Valid: true},
		Format:      updateDatasetParams.Format,
		RowCount:    pgtype.Int4{Int32: int32(updateDatasetParams.RowCount), Valid: true},
		Size:        pgtype.Int8{Int64: int64(updateDatasetParams.Size), Valid: true},
		Columns:     columns,
		FilePath:    updateDatasetParams.FilePath,
	})
	return &models.Dataset{
		ID:          d.ID,
		Name:        d.Name,
		Description: d.Description.String,
		Format:      d.Format,
		CreatedAt:   d.CreatedAt.Time,
		UpdatedAt:   d.UpdatedAt.Time,
		RowCount:    int(d.RowCount.Int32),
		Size:        int(d.Size.Int64),
		FilePath:    d.FilePath,
	}, nil
}

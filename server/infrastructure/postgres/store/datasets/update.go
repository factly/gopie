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
	columnsBytes, err := json.Marshal(updateDatasetParams.Columns)
	if err != nil {
		s.logger.Error("Error marshaling columns", zap.Error(err))
		return nil, err
	}
	d, err := s.q.UpdateDataset(ctx, gen.UpdateDatasetParams{
		ID:          datasetID,
		Description: pgtype.Text{String: updateDatasetParams.Description, Valid: true},
		RowCount:    pgtype.Int4{Int32: int32(updateDatasetParams.RowCount), Valid: true},
		Size:        pgtype.Int8{Int64: int64(updateDatasetParams.Size), Valid: true},
		Columns:     columnsBytes,
		FilePath:    updateDatasetParams.FilePath,
		Alias:       pgtype.Text{String: updateDatasetParams.Alias, Valid: true},
		UpdatedBy:   pgtype.Text{String: updateDatasetParams.UpdatedBy, Valid: true},
		OrgID:       pgtype.Text{String: updateDatasetParams.OrgID, Valid: true},
	})
	columns := make([]map[string]any, 0)
	_ = json.Unmarshal(columnsBytes, &columns)
	return &models.Dataset{
		ID:          d.ID,
		Name:        d.Name,
		Description: d.Description.String,
		CreatedAt:   d.CreatedAt.Time,
		UpdatedAt:   d.UpdatedAt.Time,
		RowCount:    int(d.RowCount.Int32),
		Size:        int(d.Size.Int64),
		FilePath:    d.FilePath,
		Columns:     columns,
		OrgID:       d.OrgID.String,
	}, nil
}

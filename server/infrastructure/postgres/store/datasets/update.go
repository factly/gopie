package datasets

import (
	"context"
	"encoding/json"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PgDatasetStore) Update(ctx context.Context, datasetID string, updateDatasetParams *models.UpdateDatasetParams) (*models.Dataset, error) {
	columnsBytes, err := json.Marshal(updateDatasetParams.Columns)
	if err != nil {
		s.logger.Error("Error marshaling columns", zap.Error(err))
		return nil, err
	}
	dID, err := uuid.Parse(datasetID)
	if err != nil {
		s.logger.Error("Error parsing dataset ID", zap.Error(err))
		return nil, err
	}

	d, err := s.q.UpdateDataset(ctx, gen.UpdateDatasetParams{
		Column9:     pgtype.UUID{Bytes: dID, Valid: true},
		RowCount:    pgtype.Int4{Int32: int32(updateDatasetParams.RowCount), Valid: updateDatasetParams.RowCount != 0},
		Size:        pgtype.Int8{Int64: int64(updateDatasetParams.Size), Valid: updateDatasetParams.Size != 0},
		Columns:     columnsBytes,
		Alias:       pgtype.Text{String: updateDatasetParams.Alias, Valid: updateDatasetParams.Alias != ""},
		Description: pgtype.Text{String: updateDatasetParams.Description, Valid: updateDatasetParams.Description != ""},
		FilePath:    updateDatasetParams.FilePath,
		UpdatedBy:   pgtype.Text{String: updateDatasetParams.UpdatedBy, Valid: true},
		OrgID:       pgtype.Text{String: updateDatasetParams.OrgID, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error updating dataset", zap.Error(err))
		return nil, err
	}

	columns := make([]map[string]any, 0)
	_ = json.Unmarshal(columnsBytes, &columns)
	return &models.Dataset{
		ID:           d.ID,
		Name:         d.Name,
		Description:  d.Description.String,
		CreatedAt:    d.CreatedAt.Time,
		UpdatedAt:    d.UpdatedAt.Time,
		RowCount:     int(d.RowCount.Int32),
		Size:         int(d.Size.Int64),
		FilePath:     d.FilePath,
		Columns:      columns,
		OrgID:        d.OrgID.String,
		CustomPrompt: d.CustomPrompt.String,
		Source:       d.Source,
	}, nil
}

func (s *PgDatasetStore) UpdateWithTx(ctx context.Context, tx pgx.Tx, datasetID string, updateDatasetParams *models.UpdateDatasetParams) (*models.Dataset, error) {
	columnsBytes, err := json.Marshal(updateDatasetParams.Columns)
	if err != nil {
		s.logger.Error("Error marshaling columns", zap.Error(err))
		return nil, err
	}

	dID, err := uuid.Parse(datasetID)
	if err != nil {
		s.logger.Error("Error parsing dataset ID", zap.Error(err))
		return nil, err
	}

	d, err := gen.New(tx).UpdateDataset(ctx, gen.UpdateDatasetParams{
		Column9:     pgtype.UUID{Bytes: dID, Valid: true},
		RowCount:    pgtype.Int4{Int32: int32(updateDatasetParams.RowCount), Valid: updateDatasetParams.RowCount != 0},
		Size:        pgtype.Int8{Int64: int64(updateDatasetParams.Size), Valid: updateDatasetParams.Size != 0},
		Columns:     columnsBytes,
		Alias:       pgtype.Text{String: updateDatasetParams.Alias, Valid: updateDatasetParams.Alias != ""},
		Description: pgtype.Text{String: updateDatasetParams.Description, Valid: updateDatasetParams.Description != ""},
		FilePath:    updateDatasetParams.FilePath,
		UpdatedBy:   pgtype.Text{String: updateDatasetParams.UpdatedBy, Valid: true},
		OrgID:       pgtype.Text{String: updateDatasetParams.OrgID, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error updating dataset with tx", zap.Error(err))
		return nil, err
	}

	columns := make([]map[string]any, 0)
	_ = json.Unmarshal(columnsBytes, &columns)
	return &models.Dataset{
		ID:           d.ID,
		Name:         d.Name,
		Description:  d.Description.String,
		CreatedAt:    d.CreatedAt.Time,
		UpdatedAt:    d.UpdatedAt.Time,
		RowCount:     int(d.RowCount.Int32),
		Size:         int(d.Size.Int64),
		FilePath:     d.FilePath,
		Columns:      columns,
		Source:       d.Source,
		OrgID:        d.OrgID.String,
		CustomPrompt: d.CustomPrompt.String,
	}, nil

}

package datasets

import (
	"context"
	"encoding/json"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PgDatasetStore) UpdateByOrgAndCreator(ctx context.Context, datasetID, orgID, createdBy string, params *models.UpdateDatasetParams) (*models.Dataset, error) {
	columnsBytes, err := json.Marshal(params.Columns)
	if err != nil {
		s.logger.Error("Error marshaling columns", zap.Error(err))
		return nil, err
	}
	dID, err := uuid.Parse(datasetID)
	if err != nil {
		s.logger.Error("Error parsing dataset ID", zap.Error(err))
		return nil, err
	}

	d, err := s.q.UpdateDatasetByOrgAndCreator(ctx, gen.UpdateDatasetByOrgAndCreatorParams{
		Description:  pgtype.Text{String: params.Description, Valid: params.Description != ""},
		RowCount:     pgtype.Int4{Int32: int32(params.RowCount), Valid: params.RowCount != 0},
		Size:         pgtype.Int8{Int64: int64(params.Size), Valid: params.Size != 0},
		FilePath:     params.FilePath,
		Columns:      columnsBytes,
		Alias:        pgtype.Text{String: params.Alias, Valid: params.Alias != ""},
		UpdatedBy:    pgtype.Text{String: params.UpdatedBy, Valid: true},
		CustomPrompt: pgtype.Text{String: params.CustomPrompt, Valid: true},
		Column9:      pgtype.UUID{Bytes: dID, Valid: true},
		OrgID:        pgtype.Text{String: orgID, Valid: true},
		CreatedBy:    pgtype.Text{String: createdBy, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error updating dataset by org and creator", zap.Error(err))
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
		Alias:        d.Alias.String,
		CreatedBy:    d.CreatedBy.String,
		UpdatedBy:    d.UpdatedBy.String,
	}, nil
}

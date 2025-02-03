package datasets

import (
	"context"
	"encoding/json"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresDatasetStore) Create(ctx context.Context, params *models.CreateDatasetParams) (*models.Dataset, error) {
	// check if project exists
	project, err := s.q.GetProject(ctx, params.ProjectID)
	if err != nil {
		s.logger.Error("Error fetching project", zap.Error(err))
		return nil, err
	}

	columns, err := json.Marshal(params.Columns)
	if err != nil {
		s.logger.Error("Error marshaling columns", zap.Error(err))
		return nil, err
	}
	d, err := s.q.CreateDataset(ctx, gen.CreateDatasetParams{
		Name:        params.Name,
		Description: pgtype.Text{String: params.Description, Valid: true},
		Format:      params.Format,
		RowCount:    pgtype.Int4{Int32: int32(params.RowCount), Valid: true},
		Size:        pgtype.Int8{Int64: int64(params.Size), Valid: true},
		FilePath:    params.FilePath,
		Columns:     columns,
	})
	if err != nil {
		s.logger.Error("Error creating dataset", zap.Error(err))
		return nil, err
	}

	err = s.q.AddDatasetToProject(ctx, gen.AddDatasetToProjectParams{
		ProjectID: project.ID,
		DatasetID: d.ID,
	})

	columnsMap := make([]map[string]any, 0)
	// we can ignore the error here as we have already marshaled the columns
	_ = json.Unmarshal(d.Columns, &columnsMap)

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
		Columns:     columnsMap,
	}, nil
}

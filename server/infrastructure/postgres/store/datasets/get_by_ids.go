package datasets

import (
	"context"
	"encoding/json"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

// GetDatasetsByIDs fetches multiple datasets by their IDs for a given organization
func (s *PgDatasetStore) GetDatasetsByIDs(ctx context.Context, datasetIDs []string, orgID string) ([]*models.Dataset, error) {
	if len(datasetIDs) == 0 {
		return []*models.Dataset{}, nil
	}

	// Use the generated sqlc batch query
	rows, err := s.q.GetDatasetsByIDs(ctx, gen.GetDatasetsByIDsParams{
		OrgID:   pgtype.Text{String: orgID, Valid: true},
		Column2: datasetIDs,
	})
	if err != nil {
		s.logger.Error("Error fetching datasets by IDs", zap.Error(err))
		return nil, err
	}

	var datasets []*models.Dataset
	for _, row := range rows {
		var columns []map[string]any
		if len(row.Columns) > 0 {
			if err := json.Unmarshal(row.Columns, &columns); err != nil {
				s.logger.Error("Error unmarshaling dataset columns", zap.Error(err))
				columns = []map[string]any{}
			}
		}

		dataset := &models.Dataset{
			ID:           row.ID,
			Name:         row.Name,
			Description:  row.Description.String,
			RowCount:     int(row.RowCount.Int32),
			Size:         int(row.Size.Int64),
			FilePath:     row.FilePath,
			Source:       row.Source,
			Columns:      columns,
			Alias:        row.Alias.String,
			CreatedBy:    row.CreatedBy.String,
			UpdatedBy:    row.UpdatedBy.String,
			OrgID:        row.OrgID.String,
			CustomPrompt: row.CustomPrompt.String,
			CreatedAt:    row.CreatedAt.Time,
			UpdatedAt:    row.UpdatedAt.Time,
		}
		datasets = append(datasets, dataset)
	}

	s.logger.Info("Successfully fetched datasets by IDs", zap.Int("count", len(datasets)))

	return datasets, nil
}

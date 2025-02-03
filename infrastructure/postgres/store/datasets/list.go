package datasets

import (
	"context"
	"encoding/json"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"go.uber.org/zap"
)

func (s *PostgresDatasetStore) List(ctx context.Context, projectID string, pagination models.Pagination) (*models.PaginationView[*models.Dataset], error) {
	ds, err := s.q.ListDatasets(ctx, gen.ListDatasetsParams{
		Limit:  int32(pagination.Limit),
		Offset: int32(pagination.Offset),
	})
	if err != nil {
		s.logger.Error("Error fetching datasets", zap.Error(err))
		return nil, err
	}

	var datasets []*models.Dataset
	for _, d := range ds {
		columns := make([]map[string]any, 0)
		_ = json.Unmarshal([]byte(d.Columns), &columns)

		datasets = append(datasets, &models.Dataset{
			ID:          d.ID,
			Name:        d.Name,
			Description: d.Description.String,
			CreatedAt:   d.CreatedAt.Time,
			UpdatedAt:   d.UpdatedAt.Time,
			Columns:     columns,
			RowCount:    int(d.RowCount.Int32),
			Size:        int(d.Size.Int64),
			FilePath:    d.FilePath,
			Format:      d.Format,
		})
	}

	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, int(0), datasets)
	return &paginationView, nil
}

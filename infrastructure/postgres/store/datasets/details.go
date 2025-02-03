package datasets

import (
	"context"
	"encoding/json"
	"time"

	"github.com/factly/gopie/domain/models"
	"go.uber.org/zap"
)

func (s *PgDatasetStore) Details(ctx context.Context, datasetID string) (*models.Dataset, error) {
	d, err := s.q.GetDataset(ctx, datasetID)
	if err != nil {
		s.logger.Error("Error fetching dataset", zap.Error(err))
		return nil, err
	}
	columns := make([]map[string]any, 0)
	err = json.Unmarshal([]byte(d.Columns), &columns)
	if err != nil {
		s.logger.Error("Error unmarshaling columns", zap.Error(err))
		return nil, err
	}

	return &models.Dataset{
		ID:          d.ID,
		Name:        d.Name,
		Description: d.Description.String,
		Format:      d.Format,
		RowCount:    int(d.RowCount.Int32),
		Size:        int(d.Size.Int64),
		FilePath:    d.FilePath,
		CreatedAt:   time.Time(d.CreatedAt.Time),
		UpdatedAt:   time.Time(d.UpdatedAt.Time),
		Columns:     columns,
	}, nil
}

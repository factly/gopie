package datasets

import (
	"context"
	"encoding/json"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"go.uber.org/zap"
)

func (s *PgDatasetStore) List(ctx context.Context, projectID string, pagination models.Pagination) (*models.PaginationView[*models.Dataset], error) {
	ds, err := s.q.ListProjectDatasets(ctx, gen.ListProjectDatasetsParams{
		ProjectID: projectID,
		Limit:     int32(pagination.Limit),
		Offset:    int32(pagination.Offset),
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
			ID:           d.ID,
			Name:         d.Name,
			Alias:        d.Alias.String,
			Description:  d.Description.String,
			CreatedAt:    d.CreatedAt.Time,
			CreatedBy:    d.CreatedBy.String,
			UpdatedAt:    d.UpdatedAt.Time,
			UpdatedBy:    d.UpdatedBy.String,
			Columns:      columns,
			RowCount:     int(d.RowCount.Int32),
			Size:         int(d.Size.Int64),
			FilePath:     d.FilePath,
			OrgID:        d.OrgID.String,
			CustomPrompt: d.CustomPrompt.String,
		})
	}

	count, err := s.q.GetProjectDatasetsCount(ctx, projectID)
	if err != nil {
		s.logger.Error("Error fetching datasets count", zap.Error(err))
		return nil, err
	}

	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, int(count), datasets)
	return &paginationView, nil
}

func (s *PgDatasetStore) ListFailedUploads(ctx context.Context) ([]*models.FailedDatasetUpload, error) {
	failedUploads, err := s.q.ListFailedDatasetUploads(ctx)
	if err != nil {
		s.logger.Error("Error fetching failed uploads", zap.Error(err))
		return nil, err
	}

	var failedUploadsList []*models.FailedDatasetUpload
	for _, f := range failedUploads {
		failedUploadsList = append(failedUploadsList, &models.FailedDatasetUpload{
			ID:        f.ID,
			DatasetID: f.DatasetID,
			Error:     f.Error,
			CreatedAt: f.CreatedAt.Time,
		})
	}

	return failedUploadsList, nil
}

func (s *PgDatasetStore) ListAllDatasets(ctx context.Context) ([]*models.Dataset, error) {
	ds, err := s.q.ListAllDatasets(ctx)
	if err != nil {
		s.logger.Error("Error fetching datasets", zap.Error(err))
		return nil, err
	}

	var datasets []*models.Dataset
	for _, d := range ds {
		columns := make([]map[string]any, 0)
		_ = json.Unmarshal([]byte(d.Columns), &columns)
		datasets = append(datasets, &models.Dataset{
			ID:           d.ID,
			Name:         d.Name,
			Alias:        d.Alias.String,
			Description:  d.Description.String,
			CreatedAt:    d.CreatedAt.Time,
			CreatedBy:    d.CreatedBy.String,
			UpdatedAt:    d.UpdatedAt.Time,
			UpdatedBy:    d.UpdatedBy.String,
			Columns:      columns,
			RowCount:     int(d.RowCount.Int32),
			Size:         int(d.Size.Int64),
			FilePath:     d.FilePath,
			OrgID:        d.OrgID.String,
			CustomPrompt: d.CustomPrompt.String,
		})
	}

	return datasets, nil
}

func (s *PgDatasetStore) ListALlDatasetsFromProject(ctx context.Context, projectID string) ([]*models.Dataset, error) {
	ds, err := s.q.ListAllDatasetsFromProject(ctx, projectID)
	if err != nil {
		s.logger.Error("Error fetching datasets", zap.Error(err))
		return nil, err
	}

	var datasets []*models.Dataset
	for _, d := range ds {
		columns := make([]map[string]any, 0)
		_ = json.Unmarshal([]byte(d.Columns), &columns)
		datasets = append(datasets, &models.Dataset{
			ID:           d.ID,
			Name:         d.Name,
			Alias:        d.Alias.String,
			Description:  d.Description.String,
			CreatedAt:    d.CreatedAt.Time,
			CreatedBy:    d.CreatedBy.String,
			UpdatedAt:    d.UpdatedAt.Time,
			UpdatedBy:    d.UpdatedBy.String,
			Columns:      columns,
			RowCount:     int(d.RowCount.Int32),
			Size:         int(d.Size.Int64),
			FilePath:     d.FilePath,
			OrgID:        d.OrgID.String,
			CustomPrompt: d.CustomPrompt.String,
		})
	}

	return datasets, nil
}

func (s *PgDatasetStore) GetProjectForDataset(ctx context.Context, datasetID string) (string, error) {
	projectID, err := s.q.GetProjectForDataset(ctx, datasetID)
	if err != nil {
		s.logger.Error("Error fetching project for dataset", zap.Error(err))
		return "", err
	}
	return projectID, nil
}

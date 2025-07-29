package datasets

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PgDatasetStore) Details(ctx context.Context, datasetID string, orgID string) (*models.Dataset, error) {
	d, err := s.q.GetDataset(ctx, gen.GetDatasetParams{
		ID:    datasetID,
		OrgID: pgtype.Text{String: orgID, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error fetching dataset", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrRecordNotFound
		}
		return nil, err
	}
	columns := make([]map[string]any, 0)
	err = json.Unmarshal([]byte(d.Columns), &columns)
	if err != nil {
		s.logger.Error("Error unmarshaling columns", zap.Error(err))
		return nil, err
	}

	return &models.Dataset{
		ID:           d.ID,
		Name:         d.Name,
		Alias:        d.Alias.String,
		Description:  d.Description.String,
		RowCount:     int(d.RowCount.Int32),
		Size:         int(d.Size.Int64),
		FilePath:     d.FilePath,
		CreatedAt:    time.Time(d.CreatedAt.Time),
		CreatedBy:    d.CreatedBy.String,
		UpdatedAt:    time.Time(d.UpdatedAt.Time),
		UpdatedBy:    d.UpdatedBy.String,
		Columns:      columns,
		OrgID:        d.OrgID.String,
		CustomPrompt: d.CustomPrompt.String,
	}, nil
}

func (s *PgDatasetStore) GetByTableName(ctx context.Context, tableName string, orgID string) (*models.Dataset, error) {
	d, err := s.q.GetDatasetByName(ctx, gen.GetDatasetByNameParams{
		Name:  tableName,
		OrgID: pgtype.Text{String: orgID, Valid: false},
	})
	if err != nil {
		s.logger.Error("Error fetching dataset", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrRecordNotFound
		}
		return nil, err
	}

	columns := make([]map[string]any, 0)
	err = json.Unmarshal([]byte(d.Columns), &columns)
	if err != nil {
		s.logger.Error("Error unmarshaling columns", zap.Error(err))
		return nil, err
	}

	return &models.Dataset{
		ID:           d.ID,
		Name:         d.Name,
		Description:  d.Description.String,
		RowCount:     int(d.RowCount.Int32),
		Size:         int(d.Size.Int64),
		FilePath:     d.FilePath,
		CreatedAt:    time.Time(d.CreatedAt.Time),
		UpdatedAt:    time.Time(d.UpdatedAt.Time),
		Columns:      columns,
		OrgID:        d.OrgID.String,
		CustomPrompt: d.CustomPrompt.String,
	}, nil
}

func (s *PgDatasetStore) GetDatasetSummary(ctx context.Context, datasetName string) (*models.DatasetSummaryWithName, error) {
	d, err := s.q.GetDatasetSummary(ctx, datasetName)
	if err != nil {
		s.logger.Error("Error fetching dataset summary", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrRecordNotFound
		}
		return nil, err
	}

	summary := []models.DatasetSummary{}
	err = json.Unmarshal([]byte(d.Summary), &summary)
	if err != nil {
		s.logger.Error("Error unmarshaling dataset summary", zap.Error(err))
		return nil, err
	}

	return &models.DatasetSummaryWithName{
		DatasetName: d.DatasetName,
		Summary:     &summary,
	}, nil
}

func (s *PgDatasetStore) GetDatasetByID(ctx context.Context, datasetID string) (*models.Dataset, error) {
	d, err := s.q.GetDatasetByID(ctx, datasetID)
	if err != nil {
		s.logger.Error("Error fetching dataset", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrRecordNotFound
		}
		return nil, err
	}
	columns := make([]map[string]any, 0)
	err = json.Unmarshal([]byte(d.Columns), &columns)
	if err != nil {
		s.logger.Error("Error unmarshaling columns", zap.Error(err))
		return nil, err
	}

	return &models.Dataset{
		ID:           d.ID,
		Name:         d.Name,
		Alias:        d.Alias.String,
		Description:  d.Description.String,
		RowCount:     int(d.RowCount.Int32),
		Size:         int(d.Size.Int64),
		FilePath:     d.FilePath,
		CreatedAt:    time.Time(d.CreatedAt.Time),
		CreatedBy:    d.CreatedBy.String,
		UpdatedAt:    time.Time(d.UpdatedAt.Time),
		UpdatedBy:    d.UpdatedBy.String,
		Columns:      columns,
		OrgID:        d.OrgID.String,
		CustomPrompt: d.CustomPrompt.String,
	}, nil
}

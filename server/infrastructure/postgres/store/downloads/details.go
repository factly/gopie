package downloads

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PgDownloadsStore) GetDownload(ctx context.Context, id, orgID string) (*models.Download, error) {
	uid, err := uuid.Parse(id)
	if err != nil {
		return nil, err
	}

	genParams := gen.GetDownloadParams{
		ID:    pgtype.UUID{Bytes: uid, Valid: true},
		OrgID: orgID,
	}

	genDownload, err := s.q.GetDownload(ctx, genParams)
	if err != nil {
		return nil, err
	}

	return models.FromGenDownload(genDownload), nil
}

func (s *PgDownloadsStore) GetDataset(ctx context.Context, datasetID string, orgID string) (*models.Dataset, error) {
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

func (s *PgDownloadsStore) FindExistingValidDownload(ctx context.Context, datasetID, userID, orgID, sql, format string) (*models.Download, bool, error) {
	params := gen.FindExistingValidDownloadParams{
		DatasetID: datasetID,
		UserID:    userID,
		OrgID:     orgID,
		Sql:       sql,
		Format:    format,
	}

	d, err := s.q.FindExistingValidDownload(ctx, params)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, false, nil
		}
		s.logger.Error("error finding existing valid download", zap.Error(err))
		return nil, false, err
	}

	return models.FromGenDownload(d), true, nil
}

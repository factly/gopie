package datasets

import (
	"context"
	"encoding/json"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PgDatasetStore) ListByProjectAndRole(ctx context.Context, projectID, orgID, createdBy string, role models.Role, pagination models.Pagination) (*models.PaginationView[*models.Dataset], error) {
	if role == models.Admin {
		// For admins, use the existing List method which lists all datasets in the project
		return s.List(ctx, projectID, pagination)
	}

	// For non-admins, list only datasets they created
	ds, err := s.q.ListDatasetsByProjectAndCreator(ctx, gen.ListDatasetsByProjectAndCreatorParams{
		ProjectID: projectID,
		OrgID:     pgtype.Text{String: orgID, Valid: true},
		CreatedBy: pgtype.Text{String: createdBy, Valid: true},
		Limit:     int32(pagination.Limit),
		Offset:    int32(pagination.Offset),
	})
	if err != nil {
		s.logger.Error("Error listing datasets by project and creator", zap.Error(err))
		return nil, err
	}

	// Convert to models
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
			Source:       d.Source,
			Columns:      columns,
			RowCount:     int(d.RowCount.Int32),
			Size:         int(d.Size.Int64),
			FilePath:     d.FilePath,
			OrgID:        d.OrgID.String,
			CustomPrompt: d.CustomPrompt.String,
		})
	}

	// Get total count for non-admin users by fetching all their datasets
	allDs, err := s.q.ListDatasetsByProjectAndCreator(ctx, gen.ListDatasetsByProjectAndCreatorParams{
		ProjectID: projectID,
		OrgID:     pgtype.Text{String: orgID, Valid: true},
		CreatedBy: pgtype.Text{String: createdBy, Valid: true},
		Limit:     1000000, // Large limit to get count
		Offset:    0,
	})
	if err != nil {
		s.logger.Error("Error getting datasets count", zap.Error(err))
		return nil, err
	}
	count := len(allDs)

	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, count, datasets)
	return &paginationView, nil
}

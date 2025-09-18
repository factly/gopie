package projects

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresProjectStore) GetProjectsByIDs(ctx context.Context, projectIDs []string, orgID string) ([]*models.Project, error) {
	if len(projectIDs) == 0 {
		return []*models.Project{}, nil
	}

	// Use the generated sqlc batch query
	rows, err := s.q.GetProjectsByIDs(ctx, gen.GetProjectsByIDsParams{
		OrgID:      pgtype.Text{String: orgID, Valid: true},
		ProjectIds: projectIDs,
	})
	if err != nil {
		s.logger.Error("Error fetching projects by IDs", zap.Error(err))
		return nil, err
	}

	var projects []*models.Project
	for _, row := range rows {
		project := &models.Project{
			ID:           row.ID,
			Name:         row.Name,
			Description:  row.Description.String,
			CreatedBy:    row.CreatedBy.String,
			UpdatedBy:    row.UpdatedBy.String,
			OrgID:        row.OrgID.String,
			CustomPrompt: row.CustomPrompt.String,
			CreatedAt:    row.CreatedAt.Time,
			UpdatedAt:    row.UpdatedAt.Time,
		}
		projects = append(projects, project)
	}

	s.logger.Info("Successfully fetched projects by IDs", zap.Int("count", len(projects)))

	return projects, nil
}

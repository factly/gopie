package projects

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresProjectStore) Update(ctx context.Context, projectID string, params *models.UpdateProjectParams) (*models.Project, error) {
	p, err := s.q.UpdateProject(ctx, gen.UpdateProjectParams{
		ID:          projectID,
		Name:        params.Name,
		Description: pgtype.Text{String: params.Description},
	})
	if err != nil {
		s.logger.Error("Error updating project", zap.Error(err))
		return nil, err
	}

	return &models.Project{
		ID:          p.ID,
		Name:        p.Name,
		Description: p.Description.String,
		CreatedAt:   p.CreatedAt.Time,
		UpdatedAt:   p.UpdatedAt.Time,
	}, nil
}

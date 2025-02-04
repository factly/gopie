package projects

import (
	"context"
	"time"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresProjectStore) Create(ctx context.Context, params models.CreateProjectParams) (*models.Project, error) {
	p, err := s.q.CreateProject(ctx, gen.CreateProjectParams{
		Name:        params.Name,
		Description: pgtype.Text{String: params.Description, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error creating project", zap.Error(err))
		return nil, err
	}

	return &models.Project{
		ID:          p.ID,
		Name:        p.Name,
		Description: p.Description.String,
		CreatedAt:   time.Time(p.CreatedAt.Time),
		UpdatedAt:   time.Time(p.UpdatedAt.Time),
	}, nil
}

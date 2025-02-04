package projects

import (
	"context"
	"errors"
	"time"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/jackc/pgx/v5"
	"go.uber.org/zap"
)

func (s *PostgresProjectStore) Details(ctx context.Context, id string) (*models.Project, error) {
	p, err := s.q.GetProject(ctx, id)
	if err != nil {
		s.logger.Error("Error fetching project", zap.Error(err))
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, domain.ErrRecordNotFound
		}
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

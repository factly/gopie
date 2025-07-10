package projects

import (
	"context"
	"errors"
	"time"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresProjectStore) Details(ctx context.Context, id, orgID string) (*models.Project, error) {
	p, err := s.q.GetProject(ctx, gen.GetProjectParams{
		ID:    id,
		OrgID: pgtype.Text{String: orgID, Valid: true},
	})
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
		CreatedBy:   p.CreatedBy.String,
		UpdatedBy:   p.UpdatedBy.String,
		OrgID:       p.OrgID.String,
	}, nil
}

func (s *PostgresProjectStore) GetProjectByID(ctx context.Context, id string) (*models.Project, error) {
	p, err := s.q.GetProjectByID(ctx, id)
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
		CreatedBy:   p.CreatedBy.String,
		UpdatedBy:   p.UpdatedBy.String,
		OrgID:       p.OrgID.String,
	}, nil
}

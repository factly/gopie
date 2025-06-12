package projects

import (
	"context"
	"time"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresProjectStore) SearchProject(ctx context.Context, query string, pagination models.Pagination, orgID string) (*models.PaginationView[*models.SearchProjectsResults], error) {
	ps, err := s.q.SearchProjects(ctx, gen.SearchProjectsParams{
		OrgID:   pgtype.Text{String: orgID, Valid: true},
		Column2: query,
		Limit:   int32(pagination.Limit),
		Offset:  int32(pagination.Offset),
	})
	if err != nil {
		s.logger.Error("Error fetching projects", zap.Error(err))
		return nil, err
	}

	var projects []*models.SearchProjectsResults
	for _, p := range ps {
		projects = append(projects, &models.SearchProjectsResults{
			ID:           p.ID,
			Name:         p.Name,
			Description:  p.Description.String,
			CreatedAt:    time.Time(p.CreatedAt.Time),
			UpdatedAt:    time.Time(p.UpdatedAt.Time),
			DatasetCount: int(p.DatasetCount),
		})
	}
	count, err := s.q.GetProjectsCount(ctx, pgtype.Text{String: orgID, Valid: true})
	if err != nil {
		s.logger.Error("Error fetching projects count", zap.Error(err))
		return nil, err
	}

	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, int(count), projects)
	return &paginationView, nil
}

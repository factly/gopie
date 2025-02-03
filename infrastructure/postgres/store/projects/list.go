package projects

import (
	"context"
	"encoding/json"
	"time"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"go.uber.org/zap"
)

func (s *PostgresProjectStore) List(ctx context.Context, pagination models.Pagination) (*models.PaginationView[*models.Project], error) {
	ps, err := s.q.ListProjects(ctx, gen.ListProjectsParams{
		Limit:  int32(pagination.Limit),
		Offset: int32(pagination.Offset),
	})
	if err != nil {
		s.logger.Error("Error fetching projects", zap.Error(err))
		return nil, err
	}

	var projects []*models.Project
	for _, p := range ps {
		projects = append(projects, &models.Project{
			ID:          p.ID,
			Name:        p.Name,
			Description: p.Description.String,
			CreatedAt:   time.Time(p.CreatedAt.Time),
			UpdatedAt:   time.Time(p.UpdatedAt.Time),
		})
	}
	count, err := s.q.GetProjectsCount(ctx)
	if err != nil {
		s.logger.Error("Error fetching projects count", zap.Error(err))
		return nil, err
	}

	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, int(count), projects)
	return &paginationView, nil
}

func (s *PostgresProjectStore) ListProjectDatasets(ctx context.Context, id string, pagination models.Pagination) (*models.PaginationView[*models.ListProjectDatasetsResults], error) {
	res, err := s.q.ListProjectDatasets(ctx, gen.ListProjectDatasetsParams{
		ProjectID: id,
		Limit:     int32(pagination.Limit),
		Offset:    int32(pagination.Offset),
	})
	if err != nil {
		s.logger.Error("Error fetching project datasets", zap.Error(err))
		return nil, err
	}

	var datasets []*models.ListProjectDatasetsResults
	for _, r := range res {
		columns := make(map[string]any)
		err := json.Unmarshal([]byte(r.Columns), &columns)
		if err != nil {
			s.logger.Error("Error unmarshaling columns", zap.Error(err))
			return nil, err
		}
		datasets = append(datasets, &models.ListProjectDatasetsResults{
			ID:          r.ID,
			Name:        r.Name,
			Description: r.Description.String,
			CreatedAt:   time.Time(r.CreatedAt.Time),
			UpdatedAt:   time.Time(r.UpdatedAt.Time),
			RowCount:    int(r.RowCount.Int32),
			Columns:     columns,
			AddedAt:     time.Time(r.AddedAt.Time),
		})
	}

	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, len(res), datasets)
	return &paginationView, nil
}

func (s *PostgresProjectStore) SearchProject(ctx context.Context, query string, pagination models.Pagination) (*models.PaginationView[*models.SearchProjectsResults], error) {
	ps, err := s.q.SearchProjects(ctx, gen.SearchProjectsParams{
		Column1: query,
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
			DatasetIds:   p.DatasetIds,
			DatasetCount: int(p.DatasetCount),
		})
	}
	count, err := s.q.GetProjectsCount(ctx)
	if err != nil {
		s.logger.Error("Error fetching projects count", zap.Error(err))
		return nil, err
	}

	paginationView := models.NewPaginationView(pagination.Offset, pagination.Limit, int(count), projects)
	return &paginationView, nil
}

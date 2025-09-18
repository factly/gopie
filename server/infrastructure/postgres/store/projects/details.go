package projects

import (
	"context"
	"errors"
	"strings"
	"time"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
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
		ID:           p.ID,
		Name:         p.Name,
		Description:  p.Description.String,
		CreatedAt:    p.CreatedAt.Time,
		UpdatedAt:    p.UpdatedAt.Time,
		CreatedBy:    p.CreatedBy.String,
		UpdatedBy:    p.UpdatedBy.String,
		OrgID:        p.OrgID.String,
		CustomPrompt: p.CustomPrompt.String,
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
		ID:           p.ID,
		Name:         p.Name,
		Description:  p.Description.String,
		CreatedAt:    time.Time(p.CreatedAt.Time),
		UpdatedAt:    time.Time(p.UpdatedAt.Time),
		CreatedBy:    p.CreatedBy.String,
		UpdatedBy:    p.UpdatedBy.String,
		OrgID:        p.OrgID.String,
		CustomPrompt: p.CustomPrompt.String,
	}, nil
}

func (s *PostgresProjectStore) ProjectsBelongToOrg(ctx context.Context, projectIDs []string, orgID string) (bool, error) {
	belongs, err := s.q.ProjectsBelongToOrg(ctx, gen.ProjectsBelongToOrgParams{
		Column1: projectIDs,
		OrgID:   pgtype.Text{String: orgID, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error checking projects belong to org", zap.Error(err))
		return false, err
	}

	return belongs, nil
}

func (s *PostgresProjectStore) DatasetsBelongToOrg(ctx context.Context, datasetNames []string, orgID string) (bool, error) {
	if len(datasetNames) > 0 && datasetNames[0] != "" && strings.HasPrefix(datasetNames[0], "gp_") {
		belongs, err := s.q.DatasetWithNamesBelongsToOrg(ctx, gen.DatasetWithNamesBelongsToOrgParams{
			Column1: datasetNames,
			OrgID:   pgtype.Text{String: orgID, Valid: true},
		})
		if err != nil {
			s.logger.Error("Error checking datasets belong to org", zap.Error(err))
			return false, err
		}
		return belongs, nil
	}

	// Convert datasetNames to []pgtype.UUID
	uuids := make([]pgtype.UUID, len(datasetNames))
	for i, name := range datasetNames {
		// Parse the string to uuid.UUID
		u := uuid.MustParse(name)
		uuids[i] = pgtype.UUID{Bytes: u, Valid: true}
	}

	belongs, err := s.q.DatasetWithIDsBelongsToOrg(ctx, gen.DatasetWithIDsBelongsToOrgParams{
		Column1: uuids,
		OrgID:   pgtype.Text{String: orgID, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error checking datasets belong to org", zap.Error(err))
		return false, err
	}

	return belongs, nil
}

package projects

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/jackc/pgx/v5/pgtype"
	"go.uber.org/zap"
)

func (s *PostgresProjectStore) UpdateByOrgAndCreator(ctx context.Context, projectID, orgID, createdBy string, params *models.UpdateProjectParams) (*models.Project, error) {
	p, err := s.q.UpdateProjectByOrgAndCreator(ctx, gen.UpdateProjectByOrgAndCreatorParams{
		Name:         params.Name,
		Description:  pgtype.Text{String: params.Description, Valid: true},
		UpdatedBy:    pgtype.Text{String: params.UpdatedBy, Valid: true},
		CustomPrompt: pgtype.Text{String: params.CustomPrompt, Valid: params.CustomPrompt != ""},
		ID:           projectID,
		OrgID:        pgtype.Text{String: orgID, Valid: true},
		CreatedBy:    pgtype.Text{String: createdBy, Valid: true},
	})
	if err != nil {
		s.logger.Error("Error updating project by org and creator", zap.Error(err))
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

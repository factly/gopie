package datasets

import (
	"context"

	"github.com/factly/gopie/domain/models"
)

func (s *PgDatasetStore) ListByProjectAndOrg(ctx context.Context, projectID, orgID string, pagination models.Pagination) (*models.PaginationView[*models.Dataset], error) {
	return s.List(ctx, projectID, pagination)
}

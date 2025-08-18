package downloads

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
)

// ListDownloadsByUser retrieves a paginated list of downloads for a specific user.
func (s *PgDownloadsStore) ListDownloadsByUser(ctx context.Context, userID, orgID string, limit, offset int32) ([]*models.Download, error) {
	genParams := gen.ListDownloadsByUserParams{
		UserID: userID,
		OrgID:  orgID,
		Limit:  limit,
		Offset: offset,
	}

	genDownloads, err := s.q.ListDownloadsByUser(ctx, genParams)
	if err != nil {
		return nil, err
	}

	return models.FromGenDownloadSlice(genDownloads), nil
}

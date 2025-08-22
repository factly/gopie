package downloads

import (
	"context"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
)

func (s *PgDownloadsStore) GetDownload(ctx context.Context, id, orgID string) (*models.Download, error) {
	uid, err := uuid.Parse(id)
	if err != nil {
		return nil, err
	}

	genParams := gen.GetDownloadParams{
		ID:    pgtype.UUID{Bytes: uid, Valid: true},
		OrgID: orgID,
	}

	genDownload, err := s.q.GetDownload(ctx, genParams)
	if err != nil {
		return nil, err
	}

	return models.FromGenDownload(genDownload), nil
}

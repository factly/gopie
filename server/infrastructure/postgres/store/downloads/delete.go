package downloads

import (
	"context"

	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
)

func (s *PgDownloadsStore) DeleteDownload(ctx context.Context, id, orgID string) error {
	uid, err := uuid.Parse(id)
	if err != nil {
		return err
	}

	genParams := gen.DeleteDownloadParams{
		ID:    pgtype.UUID{Bytes: uid, Valid: true},
		OrgID: orgID,
	}

	return s.q.DeleteDownload(ctx, genParams)
}

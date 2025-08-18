package downloads

import (
	"context"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/postgres/gen"
)

// SetDownloadToProcessing updates a download's status to 'processing'.
func (s *PgDownloadsStore) SetDownloadToProcessing(ctx context.Context, id string) (*models.Download, error) {
	uid, err := uuid.Parse(id)
	if err != nil {
		return nil, err
	}

	genDownload, err := s.q.SetDownloadToProcessing(ctx, pgtype.UUID{Bytes: uid, Valid: true})
	if err != nil {
		return nil, err
	}

	return models.FromGenDownload(genDownload), nil
}

// SetDownloadAsCompleted updates a download's status to 'completed' with its result metadata.
func (s *PgDownloadsStore) SetDownloadAsCompleted(ctx context.Context, id string, req *models.SetDownloadCompletedRequest) (*models.Download, error) {
	uid, err := uuid.Parse(id)
	if err != nil {
		return nil, err
	}

	genParams := gen.SetDownloadAsCompletedParams{
		ID:           pgtype.UUID{Bytes: uid, Valid: true},
		PreSignedUrl: pgtype.Text{String: req.PreSignedURL, Valid: true},
		ExpiresAt:    pgtype.Timestamptz{Time: req.ExpiresAt, Valid: true},
	}

	genDownload, err := s.q.SetDownloadAsCompleted(ctx, genParams)
	if err != nil {
		return nil, err
	}

	return models.FromGenDownload(genDownload), nil
}

// SetDownloadAsFailed updates a download's status to 'failed' with an error message.
func (s *PgDownloadsStore) SetDownloadAsFailed(ctx context.Context, id string, req *models.SetDownloadFailedRequest) (*models.Download, error) {
	uid, err := uuid.Parse(id)
	if err != nil {
		return nil, err
	}

	genParams := gen.SetDownloadAsFailedParams{
		ID:           pgtype.UUID{Bytes: uid, Valid: true},
		ErrorMessage: pgtype.Text{String: req.ErrorMessage, Valid: true},
	}

	genDownload, err := s.q.SetDownloadAsFailed(ctx, genParams)
	if err != nil {
		return nil, err
	}

	return models.FromGenDownload(genDownload), nil
}

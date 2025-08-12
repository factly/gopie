package models

import (
	"time"

	"github.com/factly/gopie/downlods-server/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
)

// Download represents the application-level model for a download.
type Download struct {
	ID           uuid.UUID  `json:"id"`
	SQL          string     `json:"sql"`
	DatasetID    string     `json:"dataset_id"`
	Status       string     `json:"status"`
	Format       string     `json:"format"`
	PreSignedURL *string    `json:"pre_signed_url,omitempty"`
	ErrorMessage *string    `json:"error_message,omitempty"`
	CreatedAt    time.Time  `json:"created_at"`
	UpdatedAt    time.Time  `json:"updated_at"`
	ExpiresAt    *time.Time `json:"expires_at,omitempty"`
	CompletedAt  *time.Time `json:"completed_at,omitempty"`
	UserID       string     `json:"user_id"`
	OrgID        string     `json:"org_id"`
}

// CreateDownloadRequest defines the parameters for creating a new download.
type CreateDownloadRequest struct {
	DatasetID string `json:"dataset_id"`
	UserID    string `json:"user_id"`
	OrgID     string `json:"org_id"`
	SQL       string `json:"sql"`
	Format    string `json:"format"`
}

// SetDownloadCompletedRequest defines the parameters for marking a download as completed.
type SetDownloadCompletedRequest struct {
	PreSignedURL string    `json:"pre_signed_url"`
	ExpiresAt    time.Time `json:"expires_at"`
}

type SetDownloadFailedRequest struct {
	ErrorMessage string `json:"error_message"`
}

func (req *CreateDownloadRequest) ToGenCreateDownloadParams() gen.CreateDownloadParams {
	return gen.CreateDownloadParams{
		DatasetID: req.DatasetID,
		UserID:    req.UserID,
		OrgID:     req.OrgID,
		Sql:       req.SQL,
		Format:    req.Format,
	}
}

func FromGenDownload(d gen.Download) *Download {
	return &Download{
		ID:           d.ID.Bytes,
		SQL:          d.Sql,
		DatasetID:    d.DatasetID,
		Status:       string(d.Status),
		Format:       d.Format,
		PreSignedURL: pgTextToStringPtr(d.PreSignedUrl),
		ErrorMessage: pgTextToStringPtr(d.ErrorMessage),
		CreatedAt:    d.CreatedAt.Time,
		UpdatedAt:    d.UpdatedAt.Time,
		ExpiresAt:    pgTimestampToTimePtr(d.ExpiresAt),
		CompletedAt:  pgTimestampToTimePtr(d.CompletedAt),
		UserID:       d.UserID,
		OrgID:        d.OrgID,
	}
}

func FromGenDownloadSlice(downloads []gen.Download) []*Download {
	result := make([]*Download, len(downloads))
	for i, d := range downloads {
		result[i] = FromGenDownload(d)
	}
	return result
}

func pgTextToStringPtr(t pgtype.Text) *string {
	if t.Valid {
		return &t.String
	}
	return nil
}

func pgTimestampToTimePtr(t pgtype.Timestamptz) *time.Time {
	if t.Valid {
		return &t.Time
	}
	return nil
}


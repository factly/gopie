package models

import (
	"time"

	"github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
)

// Download represents the application-level model for a download.
// @Description Download entity containing download details and status
type Download struct {
	// Unique identifier for the download
	ID uuid.UUID `json:"id" example:"550e8400-e29b-41d4-a716-446655440000"`
	// SQL query to be executed for the download
	SQL string `json:"sql" example:"SELECT * FROM users LIMIT 100"`
	// ID of the dataset being downloaded
	DatasetID string `json:"dataset_id" example:"dataset_123"`
	// Current status of the download (pending, processing, completed, failed)
	Status string `json:"status" example:"completed" enums:"pending,processing,completed,failed"`
	// Format of the download file (csv, json, parquet)
	Format string `json:"format" example:"csv" enums:"csv,json,parquet"`
	// Pre-signed URL for downloading the file (only available when completed)
	PreSignedURL *string `json:"pre_signed_url,omitempty" example:"https://s3.example.com/downloads/file.csv?signature=..."`
	// Error message if the download failed
	ErrorMessage *string `json:"error_message,omitempty" example:"Query execution failed"`
	// Timestamp when the download was created
	CreatedAt time.Time `json:"created_at" example:"2024-01-15T09:30:00Z"`
	// Timestamp when the download was last updated
	UpdatedAt time.Time `json:"updated_at" example:"2024-01-15T09:31:00Z"`
	// Timestamp when the download URL expires
	ExpiresAt *time.Time `json:"expires_at,omitempty" example:"2024-01-15T10:30:00Z"`
	// Timestamp when the download was completed
	CompletedAt *time.Time `json:"completed_at,omitempty" example:"2024-01-15T09:31:00Z"`
	// ID of the user who initiated the download
	UserID string `json:"user_id" example:"user_123"`
	// ID of the organization
	OrgID string `json:"org_id" example:"org_456"`
}

// CreateDownloadRequest defines the parameters for creating a new download.
// @Description Request body for creating a new download
type CreateDownloadRequest struct {
	// ID of the dataset to download from
	ID        string `json:"id"`
	DatasetID string `json:"dataset_id" validate:"required" example:"dataset_123"`
	UserID    string
	OrgID     string
	// SQL query to execute for the download
	SQL string `json:"sql" validate:"required" example:"SELECT * FROM users WHERE created_at > '2024-01-01'"`
	// Format of the download file (csv, json, parquet)
	Format string `json:"format" validate:"required,oneof=csv json parquet" example:"csv"`
}

// The DownloadsSSEData struct helps pass either data or an error through the channel.
type DownloadsSSEData struct {
	Data  []byte
	Error error
}

type SetDownloadCompletedRequest struct {
	PreSignedURL string    `json:"pre_signed_url"`
	ExpiresAt    time.Time `json:"expires_at"`
}

type SetDownloadFailedRequest struct {
	ErrorMessage string `json:"error_message"`
}

func (req *CreateDownloadRequest) ToGenCreateDownloadParams() gen.CreateDownloadParams {
	id := uuid.MustParse(req.ID)
	return gen.CreateDownloadParams{
		ID:        pgtype.UUID{Bytes: id, Valid: true},
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

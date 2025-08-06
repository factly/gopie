package models

import (
	"time"

	"github.com/google/uuid"
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

package models

import (
	"time"
)

// APIKey represents an API key in the system
// @Description APIKey model
type APIKey struct {
	// Unique identifier of the API key
	ID string `json:"id" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Name of the API key
	Name string `json:"name" example:"Production API Key"`
	// Hash of the API key for security
	KeyHash string
	// User who created the API key
	CreatedBy string `json:"created_by" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Description of the API key
	Description string `json:"description,omitempty" example:"API key for production environment"`
	// Last time the API key was used
	LastUsedAt *time.Time `json:"last_used_at,omitempty" example:"2024-02-05T12:00:00Z"`
	// Expiration time of the API key
	ExpiresAt *time.Time `json:"expires_at,omitempty" example:"2025-02-05T12:00:00Z"`
	// Whether the API key has been revoked
	IsRevoked bool `json:"is_revoked" example:"false"`
	// Organization ID to which the API key belongs
	OrgID string `json:"org_id" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Creation timestamp
	CreatedAt time.Time `json:"created_at" example:"2024-02-05T12:00:00Z"`
	// Last update timestamp
	UpdatedAt time.Time `json:"updated_at" example:"2024-02-05T12:00:00Z"`
}

// CreateAPIKeyParams represents parameters for creating an API key
// @Description Parameters for creating a new API key
type CreateAPIKeyParams struct {
	// Hash of the API key for security
	KeyHash string `json:"-"` // Internal use only, not exposed in JSON
	// Name of the API key
	Name string `json:"name" validate:"required" example:"Production API Key"`
	// Description of the API key
	Description string `json:"description,omitempty" example:"API key for production environment"`
	// User creating the API key
	CreatedBy string `json:"created_by" validate:"required" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Organization ID to which the API key belongs
	OrgID string `json:"org_id" validate:"required" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Optional expiration time of the API key
	ExpiresAt *time.Time `json:"expires_at,omitempty" example:"2025-02-05T12:00:00Z"`
}

// APIKeyResponse represents the response when creating an API key
// @Description Response after creating a new API key
type APIKeyResponse struct {
	// The API Key details
	APIKey APIKey `json:"apikey"`
	// The plain text API key (only returned once during creation)
	Key string `json:"key,omitempty" example:"gop_xxxxxxxxxxxxxxxxxxxx"`
}

package models

import (
	"time"
)

type APIKey struct {
	ID          string     `json:"id"`
	Name        string     `json:"name"`
	KeyHash     string     `json:"-"`
	CreatedBy   string     `json:"created_by"`
	Description string     `json:"description,omitempty"`
	LastUsedAt  *time.Time `json:"last_used_at,omitempty"`
	ExpiresAt   *time.Time `json:"expires_at,omitempty"`
	IsRevoked   bool       `json:"is_revoked"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
}

type CreateAPIKeyParams struct {
	KeyHash     string     `json:"-"`
	Name        string     `json:"name" validate:"required"`
	Description string     `json:"description,omitempty"`
	CreatedBy   string     `json:"created_by" validate:"required"`
	ExpiresAt   *time.Time `json:"expires_at,omitempty"`
}

type APIKeyResponse struct {
	APIKey APIKey `json:"apikey"`
	Key    string `json:"key,omitempty"`
}

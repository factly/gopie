package models

import "time"

type Session struct {
	ID                   string
	UserID               string
	Token                string
	ExpiresAt            time.Time
	IPAddress            *string
	UserAgent            *string
	ActiveOrganizationID *string
	CreatedAt            time.Time
	UpdatedAt            time.Time
}

type OrganizationMember struct {
	ID             string
	UserID         string
	OrganizationID string
	Role           string
	CreatedAt      time.Time
}

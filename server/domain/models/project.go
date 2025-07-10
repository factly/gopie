package models

import (
	"time"
)

// Project represents a project in the system
// @Description Project model
type Project struct {
	// Unique identifier of the project
	ID string `json:"id" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Name of the project
	Name string `json:"name" example:"My Project"`
	// Description of the project
	Description string `json:"description" example:"This is a sample project description"`
	// Creation timestamp
	CreatedAt time.Time `json:"createdAt" example:"2024-02-05T12:00:00Z"`
	// Last update timestamp
	UpdatedAt time.Time `json:"updatedAt" example:"2024-02-05T12:00:00Z"`

	CreatedBy string `json:"created_by" example:"550e8400-e29b-41d4-a716-446655440000"`
	UpdatedBy string `json:"updated_by" example:"550e8400-e29b-41d4-a716-446655440000"`
	OrgID     string `json:"org_id" example:"550e8400-e29b-41d4-a716-446655440000"`
}

// CreateProjectParams represents parameters for creating a project
// @Description Parameters for creating a new project
type CreateProjectParams struct {
	// Name of the project
	Name string `json:"name" validate:"required" example:"My Project"`
	// Description of the project
	Description string `json:"description" validate:"required" example:"This is a sample project description"`
	CreatedBy   string `json:"createdBy" example:"550e8400-e29b-41d4-a716-446655440000"`
	OrgID       string `json:"orgId" example:"550e8400-e29b-41d4-a716-446655440000"` // Organization ID to which the project belongs
}

// UpdateProjectParams represents parameters for updating a project
// @Description Parameters for updating an existing project
type UpdateProjectParams struct {
	// Name of the project
	Name string `json:"name,omitempty" example:"Updated Project Name"`
	// Description of the project
	Description string `json:"description,omitempty" example:"Updated project description"`
	UpdatedBy   string `json:"updated_by" example:"550e8400-e29b-41d4-a716-446655440000"`
}

// SearchProjectsResults represents a project with dataset count in search results
// @Description Project search result with dataset count
type SearchProjectsResults struct {
	// Unique identifier of the project
	ID string `json:"id" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Name of the project
	Name string `json:"name" example:"My Project"`
	// Description of the project
	Description string `json:"description" example:"This is a sample project description"`
	// Creation timestamp
	CreatedAt time.Time `json:"createdAt" example:"2024-02-05T12:00:00Z"`
	// Last update timestamp
	UpdatedAt time.Time `json:"updatedAt" example:"2024-02-05T12:00:00Z"`
	// Number of datasets in the project
	DatasetCount int    `json:"datasetCount" example:"5"`
	CreatedBy    string `json:"createdBy" example:"550e8400-e29b-41d4-a716-446655440000"`
	UpdatedBy    string `json:"updateBy" example:"550e8400-e29b-41d4-a716-446655440000"`
	OrgID        string `json:"orgId" example:"550e8400-e29b-41d4-a716-446655440000"` // Organization ID to which the project belongs
}

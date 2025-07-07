package models

// DatabaseSource represents a database connection source
type DatabaseSource struct {
	ID               string `json:"id"`
	ConnectionString string `json:"connection_string"`
	OrganizationID   string `json:"organization_id"`
	SQLQuery         string `json:"sql_query"`
	CreatedAt        string `json:"created_at"`
	UpdatedAt        string `json:"updated_at"`
}

// CreateDatabaseSourceParams represents the parameters needed to create a new database source
type CreateDatabaseSourceParams struct {
	ConnectionString string `json:"connection_string" validate:"required"`
	SQLQuery         string `json:"sql_query" validate:"required"`
	Alias            string `json:"alias" validate:"required,min=3"`
	Description      string `json:"description,omitempty" validate:"omitempty,min=10,max=500"`
	ProjectID        string `json:"project_id" validate:"required,uuid"`
	CreatedBy        string `json:"created_by" validate:"required"`
	Driver           string `json:"driver" validate:"required,oneof=postgres mysql" example:"postgres"`
}

// UpdateDatabaseSourceParams represents the parameters needed to update a database source
type UpdateDatabaseSourceParams struct {
	ID               string `json:"id" validate:"required,uuid"`
	ConnectionString string `json:"connection_string,omitempty"`
	SQLQuery         string `json:"sql_query,omitempty"`
	Driver           string `json:"driver,omitempty" validate:"omitempty,oneof=postgres mysql" example:"postgres"`
}

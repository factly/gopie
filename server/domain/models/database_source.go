package models

// DatabaseSource represents a database connection source
type DatabaseSource struct {
	ID               string `json:"id"`
	DatasetID        string `json:"dataset_id"`
	ConnectionString string `json:"connection_string"`
	OrganizationID   string `json:"organization_id"`
	SQLQuery         string `json:"sql_query"`
	TimestampColumn  string `json:"update_sql_query,omitempty"`
	CreatedAt        string `json:"created_at"`
	LastUpdatedAt    string `json:"last_updated_at"`
	UpdatedAt        string `json:"updated_at"`
}

// CreateDatabaseSourceParams represents the parameters needed to create a new database source
type CreateDatabaseSourceParams struct {
	ConnectionString string `json:"connection_string" validate:"required"`
	SQLQuery         string `json:"sql_query" validate:"required"`
	Alias            string `json:"alias" validate:"required,min=3"`
	Description      string `json:"description,omitempty" validate:"omitempty,min=10,max=1000"`
	ProjectID        string `json:"project_id" validate:"required,uuid"`
	DatasetID        string `json:"dataset_id,omitempty" validate:"omitempty,uuid"`
	TimestampColumn  string `json:"update_sql_query,omitempty"`
	LastUpdatedAt    string `json:"last_updated_at,omitempty" validate:"omitempty,datetime"`
	CreatedBy        string `json:"created_by" validate:"required"`
	OrganizationID   string `json:"organization_id" validate:"required,string"`
	Driver           string `json:"driver" validate:"required,oneof=postgres mysql" example:"postgres"`
}

// UpdateDatabaseSourceParams represents the parameters needed to update a database source
type UpdateDatabaseSourceParams struct {
	ID               string `json:"id" validate:"required,uuid"`
	ConnectionString string `json:"connection_string,omitempty"`
	SQLQuery         string `json:"sql_query,omitempty"`
	Driver           string `json:"driver,omitempty" validate:"omitempty,oneof=postgres mysql" example:"postgres"`
}

// UpdateDatabaseSourceLastUpdatedAtParams represents the parameters needed to update a database source
type UpdateDatabaseSourceLastUpdatedAtParams struct {
	ID            string `json:"id" validate:"required,uuid"`
	LastUpdatedAt string `json:"last_updated_at" validate:"required,datetime"`
}

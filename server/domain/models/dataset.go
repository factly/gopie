package models

import "time"

// Dataset represents a dataset in the system
// @Description Dataset model
type Dataset struct {
	// Unique identifier of the dataset
	ID string `json:"id" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Name of the dataset
	Name string `json:"name" example:"gp_Dh790Asdf17kd"`
	// Alias of the dataset
	Alias string `json:"alias" example:"sales_data_alias"`
	// Description of the dataset
	Description string `json:"description" example:"Sales data for Q1 2024"`
	// Number of rows in the dataset
	RowCount int `json:"row_count" example:"1000"`
	// Column definitions of the dataset
	Columns []map[string]any `json:"columns"`
	// Size of the dataset in bytes
	Size int `json:"size" example:"1048576"`
	// File path of the dataset
	FilePath string `json:"file_path" example:"/data/sales_data.csv"`
	// Creation timestamp
	CreatedAt time.Time `json:"created_at" example:"2024-02-05T12:00:00Z"`
	// Last update timestamp
	UpdatedAt time.Time `json:"updated_at" example:"2024-02-05T12:00:00Z"`
	// CreatedBy represents the user who created the dataset
	CreatedBy string `json:"created_by" example:"550e8400-e29b-41d4-a716-446655440000"`
	// UpdatedBy represents the user who last updated the dataset
	UpdatedBy string `json:"updated_by" example:"550e8400-e29b-41d4-a716-446655440000"`
	OrgID     string `json:"org_id" example:"550e8400-e29b-41d4-a716-446655440000"` // Organization ID to which the dataset belongs
}

// ListProjectDatasetsResults represents a dataset in project listing
// @Description Dataset listing result
type ListProjectDatasetsResults struct {
	// Unique identifier of the dataset
	ID string `json:"id" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Name of the dataset
	Name string `json:"name" example:"gp_Dh790Asdf17kd"`
	// Alias of the dataset
	Alias string `json:"alias" example:"sales_data_alias"`
	// CreatedBy represents the user who created the dataset
	CreatedBy string `json:"created_by" example:"550e8400-e29b-41d4-a716-446655440000"`
	// UpdatedBy represents the user who last updated the dataset
	UpdatedBy string `json:"updated_by" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Description of the dataset
	Description string `json:"description" example:"Sales data for Q1 2024"`
	// Creation timestamp
	CreatedAt time.Time `json:"createdAt" example:"2024-02-05T12:00:00Z"`
	// Last update timestamp
	UpdatedAt time.Time `json:"updatedAt" example:"2024-02-05T12:00:00Z"`
	// Number of rows in the dataset
	RowCount int `json:"rowCount" example:"1000"`
	// Column definitions
	Columns map[string]any `json:"columns"`
	// When the dataset was added to the project
	AddedAt time.Time `json:"addedAt" example:"2024-02-05T12:00:00Z"`
	// File path of the dataset
	FilePath string `json:"file_path" example:"/data/sales_data.csv"`
}

// UploadDatasetResult represents the result of a dataset upload
// @Description Dataset upload result
type UploadDatasetResult struct {
	// File path where the dataset was uploaded
	FilePath string `json:"file_path" example:"/data/sales_data.csv"`
	// Name of the table created for the dataset
	TableName string `json:"table_name" example:"sales_data_table"`
	// Size of the uploaded dataset in bytes
	Size int `json:"size" example:"1048576"`
}

// CreateDatasetParams represents parameters for creating a dataset
// @Description Parameters for creating a new dataset
type CreateDatasetParams struct {
	// Name of the dataset
	Name string `json:"name" example:"sales_data"`
	// Alias of the dataset
	Alias string `json:"alias" example:"sales_data_alias"`
	// User ID of the creator
	CreatedBy string `json:"created_by" example:"550e8400-e29b-41d4-a716-446655440000"`
	// UpdatedBy represents the user who last updated the dataset
	UpdatedBy string `json:"updated_by" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Description of the dataset
	Description string `json:"description" example:"Sales data for Q1 2024"`
	// ID of the project this dataset belongs to
	ProjectID string `json:"project_id" example:"550e8400-e29b-41d4-a716-446655440000"`
	// File path of the dataset
	FilePath string `json:"file_path" example:"/data/sales_data.csv"`
	// Number of rows in the dataset
	RowCount int `json:"rows" example:"1000"`
	// Column definitions
	Columns []map[string]any `json:"columns"`
	// Size of the dataset in bytes
	Size  int    `json:"size" example:"1048576"`
	OrgID string `json:"org_id" example:"550e8400-e29b-41d4-a716-446655440000"` // Organization ID to which the dataset belongs
}

// UpdateDatasetParams represents parameters for updating a dataset
// @Description Parameters for updating an existing dataset
type UpdateDatasetParams struct {
	// Description of the dataset
	Description string `json:"description" example:"Updated sales data for Q1 2024"`
	// File path of the dataset
	FilePath string `json:"file_path" example:"/data/sales_data_updated.csv"`
	// Number of rows in the dataset
	RowCount int `json:"rows" example:"1000"`
	// Column definitions
	Columns []map[string]any `json:"columns"`
	// Size of the dataset in bytes
	Size int `json:"size" example:"1048576"`
	// User ID of the updater
	UpdatedBy string `json:"updated_by" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Alias of the dataset
	Alias string `json:"alias" example:"sales_data_alias"`
}

// FailedDatasetUpload represents a failed dataset upload
// @Description Failed dataset upload record
type FailedDatasetUpload struct {
	// Unique identifier of the failed upload
	ID string `json:"id" example:"550e8400-e29b-41d4-a716-446655440000"`
	// ID of the dataset that failed to upload
	DatasetID string `json:"datasetId" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Error message describing why the upload failed
	Error string `json:"error" example:"Failed to parse CSV file"`
	// When the upload failed
	CreatedAt time.Time `json:"createdAt" example:"2024-02-05T12:00:00Z"`
}

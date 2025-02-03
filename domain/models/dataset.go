package models

import "time"

type Dataset struct {
	ID          string           `json:"id"`
	Name        string           `json:"name"`
	Description string           `json:"description"`
	Format      string           `json:"format"`
	RowCount    int              `json:"row_count"`
	Columns     []map[string]any `json:"columns"`
	Size        int              `json:"size"`
	FilePath    string           `json:"file_path"`
	CreatedAt   time.Time        `json:"created_at"`
	UpdatedAt   time.Time        `json:"updated_at"`
}

type ListProjectDatasetsResults struct {
	ID          string         `json:"id"`
	Name        string         `json:"name"`
	Description string         `json:"description"`
	CreatedAt   time.Time      `json:"createdAt"`
	UpdatedAt   time.Time      `json:"updatedAt"`
	RowCount    int            `json:"rowCount"`
	Columns     map[string]any `json:"columns"`
	AddedAt     time.Time      `json:"addedAt"`
	FilePath    string         `json:"file_path"`
}

type UploadDatasetResult struct {
	FilePath  string `json:"file_path"`
	TableName string `json:"table_name"`
	Format    string `json:"format"`
	Size      int    `json:"size"`
}

type CreateDatasetParams struct {
	Name        string           `json:"name"`
	Description string           `json:"description"`
	ProjectID   string           `json:"project_id"`
	Format      string           `json:"format"`
	FilePath    string           `json:"file_path"`
	RowCount    int              `json:"rows"`
	Columns     []map[string]any `json:"columns"`
	Size        int              `json:"size"`
}

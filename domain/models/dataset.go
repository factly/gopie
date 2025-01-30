package models

import "time"

type Dataset struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Format      string `json:"format"`
	Rows        int    `json:"rows"`
	Columns     int    `json:"columns"`
	Size        int    `json:"size"`
	CreatedAt   string `json:"created_at"`
	UpdatedAt   string `json:"updated_at"`
	DeletedAt   string `json:"deleted_at"`
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
}

type UploadDatasetResult struct {
	FilePath  string `json:"file_path"`
	TableName string `json:"table_name"`
	Format    string `json:"format"`
}

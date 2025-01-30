package models

import (
	"time"
)

type Project struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Description string    `json:"description"`
	CreatedAt   time.Time `json:"createdAt"`
	UpdatedAt   time.Time `json:"updatedAt"`
}

type CreateProjectParams struct {
	Name        string `json:"name"`
	Description string `json:"description"`
}

type UpdateProjectParams struct {
	Name        string `json:"name,omitempty"`
	Description string `json:"description,omitempty"`
}

type SearchProjectsResults struct {
	ID           string      `json:"id"`
	Name         string      `json:"name"`
	Description  string      `json:"description"`
	CreatedAt    time.Time   `json:"createdAt"`
	UpdatedAt    time.Time   `json:"updatedAt"`
	DatasetIds   interface{} `json:"datasetIds"`
	DatasetCount int         `json:"datasetCount"`
}

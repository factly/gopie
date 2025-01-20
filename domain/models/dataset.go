package models

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

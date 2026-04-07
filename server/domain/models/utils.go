package models

type RestRequest struct {
	Columns []string          `json:"columns,omitempty"`
	Sort    string            `json:"sort,omitempty"`
	Limit   int               `json:"limit,omitempty"`
	Page    int               `json:"page,omitempty"`
	Filter  map[string]string `json:"filter,omitempty"`
}

type RestParams struct {
	Filter       map[string]string
	Sort         string
	Page         int
	Limit        int
	Cols         []string
	Table        string
	ImposeLimits bool
}

type ValidationError struct {
	Field string `json:"field"`
	Tag   string `json:"tag"`
	Value string `json:"value"`
}

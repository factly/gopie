package models

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

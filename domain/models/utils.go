package models

type RestParams struct {
	Filter map[string]string
	Sort   string
	Page   int
	Limit  int
	Cols   []string
	Table  string
}

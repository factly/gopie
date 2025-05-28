package models

import "encoding/json"

// DefaultLimit is the default number of items per page
const DefaultLimit = 20

// Pagination represents pagination parameters
type Pagination struct {
	// Offset is the number of items to skip (default is 0)
	Offset int `json:"offset"`
	// Limit is the maximum number of items to return (default is 20)
	Limit int `json:"limit"`
}

// PaginationView represents a paginated view of results
type PaginationView[T any] struct {
	// Results is the list of items for the current page
	Results []T `json:"results"`
	// Offset is the number of items skipped
	Offset int `json:"offset"`
	// Limit is the maximum number of items returned
	Limit int `json:"limit"`
	// Total is the total number of items across all pages
	Total int `json:"total"`
}

// NewPagination creates a new Pagination instance with default values
func NewPagination() Pagination {
	return Pagination{
		Offset: 0,
		Limit:  DefaultLimit,
	}
}

// UnmarshalJSON implements custom JSON unmarshaling for Pagination
func (p *Pagination) UnmarshalJSON(data []byte) error {
	type PaginationAlias Pagination
	temp := &struct {
		*PaginationAlias
	}{
		PaginationAlias: (*PaginationAlias)(p),
	}

	if err := json.Unmarshal(data, &temp); err != nil {
		return err
	}

	// Set default values if not provided
	if p.Limit == 0 {
		p.Limit = DefaultLimit
	}
	return nil
}

// AutoPaginateGeneric automatically paginates the given content for a specific type T
func AutoPaginateGeneric[T any](p Pagination, content []T) PaginationView[T] {
	start := p.Offset
	if start > len(content) {
		start = len(content)
	}

	end := start + p.Limit
	if end > len(content) {
		end = len(content)
	}

	results := content[start:end]
	return FormatWithGeneric(p, len(content), results)
}

// FormatWithGeneric formats the given results into a PaginationView for a specific type T
func FormatWithGeneric[T any](p Pagination, total int, results []T) PaginationView[T] {
	return PaginationView[T]{
		Results: results,
		Offset:  p.Offset,
		Limit:   p.Limit,
		Total:   total,
	}
}

// NewPaginationView creates a new PaginationView instance
func NewPaginationView[T any](offset, limit, total int, results []T) PaginationView[T] {
	return PaginationView[T]{
		Results: results,
		Offset:  offset,
		Limit:   limit,
		Total:   total,
	}
}

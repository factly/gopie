package duckdb

import (
	"database/sql"
	"time"
)

type ColScanner interface {
	Columns() ([]string, error)
	Scan(dest ...interface{}) error
	Err() error
}

type Statement struct {
	Query            string
	Args             []any
	DryRun           bool
	Priority         int
	LongRunning      bool
	ExecutionTimeout time.Duration
}

type Type struct {
	Code             string      `json:"code"`
	Nullable         bool        `json:"nullable"`
	ArrayElementType *Type       `json:"array_element_type"`
	StructType       *StructType `json:"struct_type"`
	MapType          *MapType    `json:"map_type"`
}

type StructType struct {
	Fields []*StructType_Field `json:"fields"`
}

type StructType_Field struct {
	Name string `json:"name"`
	Type *Type  `json:"type"`
}

type MapType struct {
	KeyType   *Type `json:"key_type"`
	ValueType *Type `json:"value_type"`
}

type Result struct {
	*sql.Rows
	Schema    *StructType
	cleanupFn func() error
}

// SetCleanupFunc sets a function, which will be called when the Result is closed.
func (r *Result) SetCleanupFunc(fn func() error) {
	if r.cleanupFn != nil {
		panic("cleanup function already set")
	}
	r.cleanupFn = fn
}

func (r *Result) RowsToMap() (*[]map[string]any, error) {
	var data []map[string]any
	for r.Rows.Next() {
		d := make(map[string]any)
		err := r.MapScan(d)
		if err != nil {
			return nil, err
		}
		data = append(data, d)
	}

	return &data, nil
}

// Close wraps rows.Close and calls the Result's cleanup function (if it is set).
// Close should be idempotent.
func (r *Result) Close() error {
	firstErr := r.Rows.Close()
	if r.cleanupFn != nil {
		err := r.cleanupFn()
		if firstErr == nil {
			firstErr = err
		}

		// Prevent cleanupFn from being called multiple times.
		// NOTE: Not idempotent for error returned from cleanupFn.
		r.cleanupFn = nil
	}
	return firstErr
}

func (r *Result) MapScan(des map[string]any) error {
	return MapScan(r.Rows, des)
}

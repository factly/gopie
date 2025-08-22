package models

import (
	"database/sql"
	"fmt"
	"time"
)

type Result struct {
	*sql.Rows
	ExecutionTime time.Duration
}

func (r *Result) RowsToMap() (*[]map[string]any, error) {
	var data []map[string]any
	if r.Rows == nil {
		return nil, fmt.Errorf("rows is nil")
	}
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

// RowsToMapWithColumns returns both the data and column order information
func (r *Result) RowsToMapWithColumns() (*[]map[string]any, []string, error) {
	var data []map[string]any
	var columns []string

	if r.Rows == nil {
		return nil, nil, fmt.Errorf("rows is nil")
	}

	// get columns once at the beginning
	cols, err := r.Columns()
	if err != nil {
		return nil, nil, err
	}
	columns = cols

	for r.Rows.Next() {
		d := make(map[string]any)
		err := r.MapScan(d)
		if err != nil {
			return nil, nil, err
		}
		data = append(data, d)
	}

	return &data, columns, nil
}

func (r *Result) Close() error {
	return r.Rows.Close()
}

func (r *Result) MapScan(des map[string]any) error {
	return MapScan(r.Rows, des)
}

type ColScanner interface {
	Columns() ([]string, error)
	Scan(dest ...any) error
	Err() error
}

func MapScan(r ColScanner, dest map[string]any) error {
	// ignore r.started, since we needn't use reflect for anything.
	columns, err := r.Columns()
	if err != nil {
		return err
	}

	values := make([]any, len(columns))
	for i := range values {
		values[i] = new(any)
	}

	err = r.Scan(values...)
	if err != nil {
		return err
	}

	for i, column := range columns {
		dest[column] = *(values[i].(*any))
	}

	return r.Err()
}

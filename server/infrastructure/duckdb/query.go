package duckdb

import (
	"context"
	"encoding/csv"
	"fmt"
	"io"
	"strings"
	"time"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/duckdb/duckdbsql"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

// TableNames extracts table names from a SQL query using the DuckDB parser.
func (m *OlapDBDriver) TableNames(sql string) ([]string, error) {
	ast, err := duckdbsql.Parse(m.db, sql)
	if err != nil {
		m.logger.Error("failed to parse SQL for table name extraction", zap.String("sql", sql), zap.Error(err))
		return nil, fmt.Errorf("failed to parse SQL: %w", err)
	}

	tableNames, err := ast.TableNames()
	if err != nil {
		m.logger.Error("failed to extract table names from AST", zap.String("sql", sql), zap.Error(err))
		return nil, fmt.Errorf("failed to extract table names: %w", err)
	}
	return tableNames, nil
}

// Query executes a given SQL query string against the database.
func (m *OlapDBDriver) Query(query string, transformers ...repositories.QueryTransformer) (*models.Result, error) {
	queryID, _ := uuid.NewV7() // Ignoring error for UUID generation as it's highly unlikely
	start := time.Now()
	m.logger.Debug("executing user query", zap.String("query_id", queryID.String()), zap.String("query", query))

	transformedQuery := query
	var err error
	for _, transform := range transformers {
		transformedQuery, err = transform(transformedQuery, m.GetHelperDB())
		if err != nil {
			return nil, fmt.Errorf("error transforming sql query: %w", err)
		}
		m.logger.Debug("Transformed query: ", zap.String("query_id", queryID.String()), zap.String("query", transformedQuery))
	}

	rows, err := m.db.Query(transformedQuery)
	executionTime := time.Since(start)
	latencyInMs := executionTime.Milliseconds()

	if err != nil {
		m.logger.Error("error executing query",
			zap.String("query_id", queryID.String()),
			zap.String("query", query),
			zap.Int64("latency_ms", latencyInMs),
			zap.Error(err))
		return nil, parseError(err)
	}

	m.logger.Info("query executed successfully",
		zap.String("query_id", queryID.String()),
		zap.Int64("latency_ms", latencyInMs))

	result := models.Result{
		Rows:          rows,
		ExecutionTime: executionTime,
	}
	return &result, nil
}

// ExecuteQueryAndStreamCSV executes a query and streams the results as CSV to the provided writer.
func (m *OlapDBDriver) ExecuteQueryAndStreamCSV(ctx context.Context, sql string, writer io.Writer) error {
	// Ensure the writer is closed if it has a Close method.
	defer func() {
		if closer, ok := writer.(io.Closer); ok {
			closer.Close()
		}
	}()

	rows, err := m.db.QueryContext(ctx, sql)
	if err != nil {
		return err
	}
	defer rows.Close()

	csvWriter := csv.NewWriter(writer)
	defer csvWriter.Flush()

	// Write CSV headers from column names.
	headers, err := rows.Columns()
	if err != nil {
		return err
	}
	if err := csvWriter.Write(headers); err != nil {
		return err
	}

	// Prepare to scan row values.
	values := make([]any, len(headers))
	scanArgs := make([]any, len(values))
	for i := range values {
		scanArgs[i] = &values[i]
	}

	// Iterate over rows and write to CSV.
	for rows.Next() {
		if err := rows.Scan(scanArgs...); err != nil {
			return err
		}

		record := make([]string, len(values))
		for i, val := range values {
			if val == nil {
				record[i] = "" // Represent NULL as an empty string.
			} else {
				record[i] = fmt.Sprintf("%v", val)
			}
		}

		if err := csvWriter.Write(record); err != nil {
			return err
		}
	}

	// Check for any errors encountered during iteration.
	return rows.Err()
}

// ExecuteQueryAndStoreInS3 executes a query and stores the result in S3.
func (m *OlapDBDriver) ExecuteQueryAndStoreInS3(ctx context.Context, sql, format, outputPath string) error {
	var formatOptions string
	switch strings.ToUpper(format) {
	case "CSV":
		formatOptions = "(format 'csv', header)"
	case "PARQUET":
		formatOptions = "(format 'parquet')"
	case "JSON":
		formatOptions = "(format 'json')"
	default:
		return fmt.Errorf("unsupported format: %s. Please use csv, parquet, or json", format)
	}

	finalSQL := fmt.Sprintf("COPY (%s) TO '%s' %s;", sql, outputPath, formatOptions)

	m.logger.Info("Executing export command", zap.String("sql", finalSQL))

	rows, err := m.db.QueryContext(ctx, finalSQL)
	if err != nil {
		return err
	}
	rows.Close()

	return nil
}

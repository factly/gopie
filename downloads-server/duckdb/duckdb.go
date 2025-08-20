package duckdb

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/csv"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"
	"time"

	"github.com/xitongsys/parquet-go/schema"
	"github.com/xitongsys/parquet-go/writer"

	"github.com/factly/gopie/downlods-server/models"
	"github.com/factly/gopie/downlods-server/pkg/config"
	"github.com/factly/gopie/downlods-server/pkg/logger"
	"github.com/google/uuid"
	"github.com/marcboeker/go-duckdb/v2"
	_ "github.com/marcboeker/go-duckdb/v2" // DuckDB driver for MotherDuck
	"go.uber.org/zap"

	"github.com/xuri/excelize/v2"
)

// OlapDBDriver holds the necessary components for a MotherDuck connection.
type OlapDBDriver struct {
	db     *sql.DB
	logger *logger.Logger
	dbName string
}

// NewMotherDuckDriver initializes a new MotherDuck driver.
// It assumes access_mode is always read_only.
func NewMotherDuckDriver(cfg *config.OlapDBConfig, logger *logger.Logger) (*OlapDBDriver, error) {
	olap := OlapDBDriver{
		logger: logger,
		dbName: cfg.DBName,
	}
	logger.Info("initializing motherduck driver",
		zap.String("db_name", cfg.DBName),
		zap.String("access_mode", "read_only"))

	err := olap.Connect(cfg)
	if err != nil {
		logger.Error("failed to connect to motherduck",
			zap.String("db_name", cfg.DBName),
			zap.Error(err))
		return nil, err
	}
	logger.Info("successfully connected to motherduck",
		zap.String("db_name", cfg.DBName))

	return &olap, nil
}

// Query executes a given SQL query string against the database.
func (m *OlapDBDriver) Query(query string) (*models.Result, error) {
	queryID, _ := uuid.NewV7() // Ignoring error for UUID generation as it's highly unlikely
	start := time.Now()
	m.logger.Debug("executing user query", zap.String("query_id", queryID.String()), zap.String("query", query))

	rows, err := m.db.Query(query)
	latencyInMs := time.Since(start).Milliseconds()

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
		Rows: rows,
	}
	return &result, nil
}

// GetHelperDB returns the main database connection.
func (m *OlapDBDriver) GetHelperDB() any {
	return m.db
}

// parseError unwraps the underlying duckdb-specific error for better context.
func parseError(err error) error {
	if err == nil {
		return nil
	}

	var duckErr *duckdb.Error
	if errors.As(err, &duckErr) {
		// The error still comes from the underlying duckdb driver
		return fmt.Errorf("DuckDB %v error: %w", duckErr.Type, err)
	}
	return err
}

// Connect establishes the database connection with read_only access.
func (m *OlapDBDriver) Connect(cfg *config.OlapDBConfig) error {
	// This function builds the DSN for MotherDuck and opens the sql.DB connection.
	// Access mode is now always read_only.
	if cfg.Token == "" {
		return errors.New("motherduck token is required")
	}
	dsn := fmt.Sprintf("md:%s?motherduck_token=%s&access_mode=read_only", cfg.DBName, cfg.Token)

	var err error
	m.db, err = sql.Open("duckdb", dsn)
	if err != nil {
		return err
	}
	// Ping the database to verify the connection.
	return m.db.Ping()
}

// Close closes the main database connection.
func (m *OlapDBDriver) Close() error {
	if m.db != nil {
		return m.db.Close()
	}
	return nil
}

func (m *OlapDBDriver) ExecuteQueryAndStreamJSON(ctx context.Context, sql string, writer io.Writer) error {
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

	headers, err := rows.Columns()
	if err != nil {
		return err
	}

	if _, err := writer.Write([]byte("[")); err != nil {
		return err
	}

	values := make([]any, len(headers))
	scanArgs := make([]any, len(values))
	for i := range values {
		scanArgs[i] = &values[i]
	}

	first := true
	for rows.Next() {
		if err := rows.Scan(scanArgs...); err != nil {
			return err
		}

		if !first {
			if _, err := writer.Write([]byte(",")); err != nil {
				return err
			}
		}
		first = false

		rowData := make(map[string]any, len(headers))
		for i, val := range values {
			colName := headers[i]

			if b, ok := val.([]byte); ok {
				rowData[colName] = string(b)
			} else {
				rowData[colName] = val
			}
		}

		jsonBytes, err := json.Marshal(rowData)
		if err != nil {
			return err
		}

		if _, err := writer.Write(jsonBytes); err != nil {
			return err
		}
	}

	if err := rows.Err(); err != nil {
		return err
	}

	if _, err := writer.Write([]byte("]")); err != nil {
		return err
	}

	return nil
}

func (m *OlapDBDriver) ExecuteQueryAndStreamExcel(ctx context.Context, sql string, writer io.Writer) error {
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

	f := excelize.NewFile()
	streamWriter, err := f.NewStreamWriter("Sheet1")
	if err != nil {
		return err
	}

	headers, err := rows.Columns()
	if err != nil {
		return err
	}
	headerRow := make([]any, len(headers))
	for i, h := range headers {
		headerRow[i] = h
	}
	if err := streamWriter.SetRow("A1", headerRow); err != nil {
		return err
	}

	values := make([]any, len(headers))
	scanArgs := make([]any, len(values))
	for i := range values {
		scanArgs[i] = &values[i]
	}

	rowNum := 2
	for rows.Next() {
		if err := rows.Scan(scanArgs...); err != nil {
			return err
		}

		cell, err := excelize.CoordinatesToCellName(1, rowNum)
		if err != nil {
			return err
		}

		if err := streamWriter.SetRow(cell, values); err != nil {
			return err
		}
		rowNum++
	}

	if err := rows.Err(); err != nil {
		return err
	}

	if err := streamWriter.Flush(); err != nil {
		return err
	}

	return f.Write(writer)
}

// ExecuteQueryAndStreamCSV executes a query and streams the results as a CSV file.
func (m *OlapDBDriver) ExecuteQueryAndStreamCSV(ctx context.Context, sql string, writer io.Writer) error {
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

	return rows.Err()
}

// ExecuteQueryAndStreamParquet executes a query and streams the results as a Parquet file.
// It builds the file in an in-memory buffer first to prevent race conditions with the final writer.
func (d *OlapDBDriver) ExecuteQueryAndStreamParquet(ctx context.Context, query string, finalWriter io.Writer) error {
	// The calling function is responsible for closing the finalWriter.
	defer func() {
		if closer, ok := finalWriter.(io.Closer); ok {
			closer.Close()
		}
	}()

	d.logger.Info("Executing query for Parquet streaming", zap.String("query", query))

	rows, err := d.db.QueryContext(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to execute query: %w", err)
	}
	defer rows.Close()

	colTypes, err := rows.ColumnTypes()
	if err != nil {
		return fmt.Errorf("failed to get column types: %w", err)
	}

	// Dynamically create the Parquet schema from database column types.
	s, err := createParquetSchema(colTypes)
	if err != nil {
		return fmt.Errorf("failed to create parquet schema: %w", err)
	}
	d.logger.Debug("Generated Parquet schema", zap.String("schema", s))

	sh, err := schema.NewSchemaHandlerFromJSON(s)
	if err != nil {
		return fmt.Errorf("failed to create parquet schema handler: %w", err)
	}

	buf := new(bytes.Buffer)

	pw, err := writer.NewParquetWriterFromWriter(buf, sh, 1)
	if err != nil {
		return fmt.Errorf("failed to create parquet writer: %w", err)
	}

	vals := make([]any, len(colTypes))
	scanArgs := make([]any, len(vals))
	for i := range vals {
		scanArgs[i] = &vals[i]
	}

	var rowsWritten int64
	for rows.Next() {
		if err := rows.Scan(scanArgs...); err != nil {
			return fmt.Errorf("failed to scan row: %w", err)
		}

		row := make([]any, len(vals))
		for i, v := range vals {
			switch t := v.(type) {
			case nil:
				row[i] = nil
			case int64, int32, float64, float32, bool, string:
				row[i] = t
			case []byte:
				row[i] = string(t)
			case time.Time:
				row[i] = t
			default:
				row[i] = fmt.Sprintf("%v", t)
			}
		}

		if err := pw.Write(row); err != nil {
			return fmt.Errorf("failed to write parquet row: %w", err)
		}
		rowsWritten++
	}

	if err := rows.Err(); err != nil {
		return fmt.Errorf("error during row iteration: %w", err)
	}

	if err := pw.WriteStop(); err != nil {
		d.logger.Error("Failed to stop parquet writer", zap.Error(err))
		return fmt.Errorf("failed to stop parquet writer: %w", err)
	}

	d.logger.Info("Parquet file successfully created in memory", zap.Int64("rows_written", rowsWritten), zap.Int("buffer_size_bytes", buf.Len()))

	if _, err := io.Copy(finalWriter, buf); err != nil {
		return fmt.Errorf("failed to copy buffer to final writer: %w", err)
	}

	return nil
}

func createParquetSchema(colTypes []*sql.ColumnType) (string, error) {
	type ParquetField struct {
		Tag string `json:"Tag"`
	}

	fields := make([]ParquetField, len(colTypes))
	for i, col := range colTypes {
		fields[i] = ParquetField{Tag: getParquetFieldTag(col)}
	}

	type Schema struct {
		Tag    string         `json:"Tag"`
		Fields []ParquetField `json:"Fields"`
	}

	schemaRoot := Schema{
		Tag:    "name=parquet_go_root, repetitiontype=REQUIRED",
		Fields: fields,
	}

	schemaJSON, err := json.Marshal(schemaRoot)
	if err != nil {
		return "", fmt.Errorf("failed to marshal parquet schema to JSON: %w", err)
	}
	return string(schemaJSON), nil
}

func getParquetFieldTag(colType *sql.ColumnType) string {
	dbType := strings.ToUpper(colType.DatabaseTypeName())
	colName := colType.Name()

	repetitionType := "OPTIONAL"

	var typeStr string
	switch dbType {
	case "BOOLEAN", "BOOL":
		typeStr = "type=BOOLEAN"
	case "TINYINT", "SMALLINT", "INT2", "INTEGER", "INT", "INT4":
		typeStr = "type=INT32"
	case "BIGINT", "HUGEINT", "INT8":
		typeStr = "type=INT64"
	case "FLOAT", "REAL", "FLOAT4":
		typeStr = "type=FLOAT"
	case "DOUBLE", "DECIMAL", "NUMERIC", "FLOAT8":
		typeStr = "type=DOUBLE"
	case "DATE":
		typeStr = "type=DATE"
	case "TIMESTAMP", "TIMESTAMP WITH TIME ZONE", "TIMESTAMPTZ", "DATETIME":
		typeStr = "type=TIMESTAMP_MILLIS"
	case "VARCHAR", "TEXT", "STRING", "CHAR", "BPCHAR", "UUID":
		typeStr = "type=BYTE_ARRAY, convertedtype=UTF8"
	case "BLOB", "BYTEA", "BINARY", "VARBINARY":
		typeStr = "type=BYTE_ARRAY"
	default:
		typeStr = "type=BYTE_ARRAY, convertedtype=UTF8"
	}

	return fmt.Sprintf("name=%s, %s, repetitiontype=%s", colName, typeStr, repetitionType)
}

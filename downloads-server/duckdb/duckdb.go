package duckdb

import (
	"context"
	"database/sql"
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"time"

	"github.com/factly/gopie/downlods-server/models"
	"github.com/factly/gopie/downlods-server/pkg/config"
	"github.com/factly/gopie/downlods-server/pkg/logger"
	"github.com/google/uuid"
	"github.com/marcboeker/go-duckdb/v2"
	_ "github.com/marcboeker/go-duckdb/v2" // DuckDB driver for MotherDuck
	"go.uber.org/zap"
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

// ExecuteQueryAndStreamCSV executes a query and streams the results as a CSV file.
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

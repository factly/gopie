package duckdb

import (
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/factly/gopie/downlods-server/models"
	"github.com/factly/gopie/downlods-server/pkg/config"
	"github.com/factly/gopie/downlods-server/pkg/logger"
	"github.com/google/uuid"
	"github.com/marcboeker/go-duckdb/v2"
	_ "github.com/marcboeker/go-duckdb/v2" // DuckDB driver
	"go.uber.org/zap"
)

// OlapDBDriver holds the necessary components for a DuckDB connection.
type OlapDBDriver struct {
	db       *sql.DB
	logger   *logger.Logger
	olapType string // "duckdb" or "motherduck"
	dbName   string
	// S3 configuration to reapply for each S3 operation
	s3Config *config.S3Config
}

// NewOlapDBDriver initializes a new DuckDB/MotherDuck driver.
// It assumes access_mode is always read_only.
func NewOlapDBDriver(cfg *config.OlapDBConfig, logger *logger.Logger, s3Cfg *config.S3Config) (*OlapDBDriver, error) {
	olap := OlapDBDriver{
		logger:   logger,
		s3Config: s3Cfg, // Store S3 config for later use
	}
	logger.Info("initializing duckdb driver",
		zap.String("db_type", cfg.DB),
		zap.String("access_mode", "read_only"))

	err := olap.Connect(cfg)
	if err != nil {
		logger.Error("failed to connect to duckdb",
			zap.String("db_type", cfg.DB),
			zap.Error(err))
		return nil, err
	}
	logger.Info("successfully connected to duckdb",
		zap.String("db_type", cfg.DB))

	if cfg.DB == "motherduck" {
		olap.dbName = cfg.MotherDuck.DBName
	}

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

// GetHelperDB returns the main database connection, as helperDB is no longer used.
func (m *OlapDBDriver) GetHelperDB() any {
	return m.db
}

func parseError(err error) error {
	if err == nil {
		return nil
	}

	var duckErr *duckdb.Error
	if errors.As(err, &duckErr) {
		return fmt.Errorf("DuckDB %v error: %w", duckErr.Type, err)
	}
	return err
}

// Connect establishes the database connection with read_only access.
func (m *OlapDBDriver) Connect(cfg *config.OlapDBConfig) error {
	// This function builds the DSN and opens the sql.DB connection.
	// Access mode is now always read_only.
	dsn := ""
	if cfg.DB == "motherduck" {
		dsn = fmt.Sprintf("md:%s?motherduck_token=%s&access_mode=read_only", cfg.MotherDuck.DBName, "TOKEN")
	} else {
		dsn = fmt.Sprintf("%s?access_mode=read_only", cfg.DuckDB.Path)
	}

	var err error
	m.db, err = sql.Open("duckdb", dsn)
	if err != nil {
		return err
	}
	return m.db.Ping()
}

// Close closes the main database connection.
func (m *OlapDBDriver) Close() error {
	if m.db != nil {
		return m.db.Close()
	}
	return nil
}

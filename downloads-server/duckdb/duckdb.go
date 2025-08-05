package duckdb

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
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

	// Run post-connection setup only for local DuckDB instances needing S3 config
	if cfg.DB == "duckdb" {
		err = olap.setupDuckDBHttpFs(s3Cfg)
		if err != nil {
			logger.Error("failed to run post-connection setup for duckdb",
				zap.String("db_type", cfg.DB),
				zap.Error(err))
			olap.Close() // Attempt to close main DB connection
			return nil, err
		}
		logger.Info("completed duckdb post-connection setup successfully")
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

// setupDuckDBHttpFs runs setup commands for local DuckDB, primarily for S3 (httpfs).
func (m *OlapDBDriver) setupDuckDBHttpFs(s3Cfg *config.S3Config) error {
	m.logger.Debug("starting post-connection setup for httpfs/S3")
	commands := m.generateHttpFsCommands(s3Cfg)

	tx, err := m.db.BeginTx(context.Background(), nil)
	if err != nil {
		m.logger.Error("failed to begin transaction for httpfs setup", zap.Error(err))
		return fmt.Errorf("failed to begin transaction for httpfs setup: %w", err)
	}
	defer tx.Rollback() // Rollback if commit is not successful or if there's a panic

	for _, cmd := range commands {
		m.logger.Debug("executing httpfs setup command", zap.String("command", cmd))
		if _, err := tx.Exec(cmd); err != nil {
			m.logger.Error("failed to execute httpfs setup command",
				zap.String("command", cmd),
				zap.Error(err))
			return fmt.Errorf("failed executing httpfs setup command '%s': %w", cmd, err)
		}
	}

	if err := tx.Commit(); err != nil {
		m.logger.Error("failed to commit transaction for httpfs setup", zap.Error(err))
		return fmt.Errorf("failed to commit httpfs setup: %w", err)
	}

	m.logger.Info("S3/httpfs configuration completed successfully",
		zap.String("endpoint", s3Cfg.Endpoint),
		zap.String("region", s3Cfg.Region),
		zap.Bool("ssl_enabled", s3Cfg.SSL))
	return nil
}

// generateHttpFsCommands generates the SQL commands for httpfs and S3 configuration.
func (m *OlapDBDriver) generateHttpFsCommands(s3Cfg *config.S3Config) []string {
	// Base commands for httpfs, postgres, and mysql extensions
	baseCommands := []string{
		"INSTALL httpfs;", "LOAD httpfs;",
		"INSTALL postgres;", "LOAD postgres;",
		"INSTALL mysql;", "LOAD mysql;",
	}

	// S3 specific commands
	s3Commands := []string{}
	if s3Cfg.AccessKey != "" {
		s3Commands = append(s3Commands, fmt.Sprintf("SET s3_access_key_id='%s';", s3Cfg.AccessKey))
	}
	if s3Cfg.SecretKey != "" {
		s3Commands = append(s3Commands, fmt.Sprintf("SET s3_secret_access_key='%s';", s3Cfg.SecretKey))
	}
	if s3Cfg.Endpoint != "" {
		// remove protocol if present
		endpoint := s3Cfg.Endpoint
		if strings.HasPrefix(s3Cfg.Endpoint, "http://") || strings.HasPrefix(s3Cfg.Endpoint, "https://") {
			endpoint = strings.TrimPrefix(endpoint, "http://")
			endpoint = strings.TrimPrefix(endpoint, "https://")
		}
		s3Commands = append(s3Commands, fmt.Sprintf("SET s3_endpoint='%s';", endpoint))
	}
	if s3Cfg.Region != "" {
		s3Commands = append(s3Commands, fmt.Sprintf("SET s3_region='%s';", s3Cfg.Region))
	}
	s3Commands = append(s3Commands, fmt.Sprintf("SET s3_use_ssl=%v;", s3Cfg.SSL))
	s3Commands = append(s3Commands, "SET s3_url_style='path';")

	return append(baseCommands, s3Commands...)
}

// Connect establishes the database connection with read_only access.
func (m *OlapDBDriver) Connect(cfg *config.OlapDBConfig) error {
	// This function builds the DSN and opens the sql.DB connection.
	// Access mode is now always read_only.
	dsn := "local.db?access_mode=read_only" // Example DSN for local duckdb
	if cfg.DB == "motherduck" {
		dsn = fmt.Sprintf("md:%s?motherduck_token=%s&access_mode=read_only", cfg.MotherDuck.DBName, "TOKEN")
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

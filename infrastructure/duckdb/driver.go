package duckdb

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/google/uuid"
	"github.com/huandu/go-sqlbuilder"
	"github.com/marcboeker/go-duckdb"
	_ "github.com/marcboeker/go-duckdb"
	"go.uber.org/zap"
)

type OlapDBDriver struct {
	db     *sql.DB
	logger *logger.Logger
}

// NewOlapDBDriver initializes a new DuckDB/MotherDuck driver.
func NewOlapDBDriver(cfg *config.OlapDBConfig, logger *logger.Logger, s3Cfg *config.S3Config) (repositories.OlapRepository, error) {
	olap := OlapDBDriver{
		logger: logger,
	}
	logger.Info("initializing duckdb driver",
		zap.String("db_type", cfg.DB),
		zap.String("access_mode", cfg.AccessMode))

	err := olap.Connect(cfg)
	if err != nil {
		logger.Error("failed to connect to duckdb",
			zap.String("db_type", cfg.DB),
			zap.Error(err))
		return nil, err
	}
	logger.Info("successfully connected to duckdb",
		zap.String("db_type", cfg.DB))

	// Run post-connection setup only for local DuckDB instances needing S3 config
	if cfg.DB == "duckdb" {
		err = olap.postDuckDbConnect(s3Cfg)
		if err != nil {
			logger.Error("failed to run post-connection setup",
				zap.String("db_type", cfg.DB),
				zap.Error(err))
			olap.Close()
			return nil, err
		}
		logger.Info("completed post-connection setup successfully")
	}
	return &olap, nil
}

// Connect establishes the database connection.
func (m *OlapDBDriver) Connect(cfg *config.OlapDBConfig) error {
	var dsn string
	if cfg.DB == "motherduck" {
		dsn = fmt.Sprintf("md:%s?motherduck_token=%s", cfg.MotherDuck.DBName, cfg.MotherDuck.Token)
		if cfg.AccessMode != "" {
			dsn = fmt.Sprintf("%s&access_mode=%s", dsn, cfg.AccessMode)
			m.logger.Debug("setting motherduck access mode",
				zap.String("mode", cfg.AccessMode))
		}
	} else {
		dsn = cfg.DuckDB.Path
		params := []string{}

		if cfg.DuckDB.CPU > 0 {
			params = append(params, fmt.Sprintf("threads=%d", cfg.DuckDB.CPU))
			m.logger.Debug("setting CPU threads",
				zap.Int("threads", cfg.DuckDB.CPU))
		}

		if cfg.DuckDB.MemoryLimit > 0 {
			params = append(params, fmt.Sprintf("memory_limit=%dMB", cfg.DuckDB.MemoryLimit))
			m.logger.Debug("setting memory limit",
				zap.Int("limit_mb", cfg.DuckDB.MemoryLimit))
		}

		if cfg.AccessMode != "" {
			params = append(params, fmt.Sprintf("access_mode=%s", cfg.AccessMode))
			m.logger.Debug("setting duckdb access mode",
				zap.String("mode", cfg.AccessMode))
		}

		if len(params) > 0 {
			dsn = fmt.Sprintf("%s?%s", dsn, strings.Join(params, "&"))
		}

		m.logger.Debug("constructed duckdb connection string",
			zap.String("dsn", dsn))
	}

	db, err := sql.Open("duckdb", dsn)
	if err != nil {
		m.logger.Error("failed to open database connection",
			zap.String("db_type", cfg.DB),
			zap.Error(err))
		return err // Return the original error
	}

	if err := db.Ping(); err != nil {
		m.logger.Error("failed to ping database after opening connection",
			zap.String("db_type", cfg.DB),
			zap.Error(err))
		db.Close()
		return err
	}

	m.db = db
	return nil
}

// postDuckDbConnect runs setup commands after connecting to a local DuckDB instance,
// primarily for configuring S3 access via the httpfs extension.
func (m *OlapDBDriver) postDuckDbConnect(s3Cfg *config.S3Config) error {
	m.logger.Debug("starting post-connection setup for httpfs/S3")

	// Using simple Exec as sqlbuilder is not needed for these specific commands.
	commands := []string{
		"INSTALL httpfs;",
		"LOAD httpfs;",
		fmt.Sprintf("SET s3_access_key_id='%s';", s3Cfg.AccessKey),     // Quote string values
		fmt.Sprintf("SET s3_secret_access_key='%s';", s3Cfg.SecretKey), // Quote string values
		fmt.Sprintf("SET s3_endpoint='%s';", s3Cfg.Endpoint),           // Quote string values
		fmt.Sprintf("SET s3_region='%s';", s3Cfg.Region),               // Quote string values
		"SET s3_use_ssl=true;",                                         // Use boolean literal
		fmt.Sprintf("SET s3_use_ssl=%v;", s3Cfg.SSL),                   // Use %v for boolean
		"SET s3_url_style='path';",                                     // Quote string literal 'path'
	}

	filteredCommands := []string{}
	for _, cmd := range commands {
		if (strings.Contains(cmd, "s3_endpoint=") && s3Cfg.Endpoint == "") ||
			(strings.Contains(cmd, "s3_region=") && s3Cfg.Region == "") {
			continue
		}
		filteredCommands = append(filteredCommands, cmd)
	}

	tx, err := m.db.BeginTx(context.Background(), nil)
	if err != nil {
		m.logger.Error("failed to begin transaction for post-connection setup", zap.Error(err))
		return fmt.Errorf("failed to begin transaction for post-connection setup: %w", err)
	}

	for _, cmd := range filteredCommands {
		m.logger.Debug("executing post-connect command", zap.String("command", cmd))
		_, err := tx.Exec(cmd)
		if err != nil {
			m.logger.Error("failed to execute post-connection command",
				zap.String("command", cmd),
				zap.Error(err))
			if rbErr := tx.Rollback(); rbErr != nil {
				m.logger.Error("failed to rollback transaction after command failure", zap.Error(rbErr))
			}
			return fmt.Errorf("failed executing '%s': %w", cmd, err)
		}
	}

	if err := tx.Commit(); err != nil {
		m.logger.Error("failed to commit transaction for post-connection setup", zap.Error(err))
		return fmt.Errorf("failed to commit post-connection setup: %w", err)
	}

	m.logger.Info("S3 configuration completed successfully",
		zap.String("endpoint", s3Cfg.Endpoint),
		zap.String("region", s3Cfg.Region),
		zap.Bool("ssl_enabled", s3Cfg.SSL))

	return nil
}

func (m *OlapDBDriver) Close() error {
	if m.db != nil {
		m.logger.Info("closing duckdb connection")
		return m.db.Close()
	}
	return nil
}

func (m *OlapDBDriver) CreateTable(filePath, tableName, format string, alterColumnNames map[string]string) error {
	sb := sqlbuilder.NewSelectBuilder()
	sb.Select("*")

	var readFunc string
	escapedFilePath := sqlbuilder.Escape(filePath)

	switch format {
	case "parquet":
		readFunc = fmt.Sprintf("read_parquet('%s')", escapedFilePath)
	case "csv":
		readFunc = fmt.Sprintf("read_csv_auto('%s')", escapedFilePath)
	case "json":
		readFunc = fmt.Sprintf("read_json_auto('%s')", escapedFilePath)
	default:
		return fmt.Errorf("unsupported format for CreateTable: %s", format)
	}
	sb.From(readFunc)

	readSql, readArgs := sb.Build()
	if len(readArgs) > 0 {
		m.logger.Error("unexpected arguments generated for read query", zap.Any("args", readArgs))
		return fmt.Errorf("unexpected arguments in read query construction")
	}

	createSql := fmt.Sprintf(`CREATE OR REPLACE TABLE %s AS (%s)`, sqlbuilder.Escape(tableName), readSql)

	m.logger.Debug("preparing to create table", zap.String("query", createSql))

	tx, err := m.db.BeginTx(context.Background(), nil)
	if err != nil {
		m.logger.Error("error starting transaction for CreateTable", zap.Error(err))
		return err
	}

	_, err = tx.Exec(createSql)
	if err != nil {
		m.logger.Error("error executing create table query", zap.String("query", createSql), zap.Error(err))
		if rollbackErr := tx.Rollback(); rollbackErr != nil {
			m.logger.Error("error rolling back transaction after create failure", zap.Error(rollbackErr))
		}
		return parseError(fmt.Errorf("failed creating table '%s': %w", tableName, err))
	}
	m.logger.Info("successfully created/replaced table", zap.String("tableName", tableName))

	if alterColumnNames != nil && len(alterColumnNames) > 0 {
		m.logger.Debug("renaming columns", zap.String("tableName", tableName), zap.Int("count", len(alterColumnNames)))
		escapedTableName := sqlbuilder.Escape(tableName)
		for old, new := range alterColumnNames {
			escapedOldCol := sqlbuilder.Escape(old)
			escapedNewCol := sqlbuilder.Escape(new)

			alterSql := fmt.Sprintf(`ALTER TABLE %s RENAME COLUMN %s TO %s`, escapedTableName, escapedOldCol, escapedNewCol)
			m.logger.Debug("executing alter query", zap.String("query", alterSql))

			_, err = tx.Exec(alterSql)
			if err != nil {
				m.logger.Error("error executing alter column query", zap.String("query", alterSql), zap.Error(err))
				if rollbackErr := tx.Rollback(); rollbackErr != nil {
					m.logger.Error("error rolling back transaction after alter failure", zap.Error(rollbackErr))
				}
				return parseError(fmt.Errorf("failed renaming column '%s' to '%s' in table '%s': %w", old, new, tableName, err))
			}
		}
		m.logger.Info("successfully renamed columns", zap.String("tableName", tableName))
	}

	// Commit the transaction
	if err = tx.Commit(); err != nil {
		m.logger.Error("error committing transaction for CreateTable", zap.Error(err))
		if rollbackErr := tx.Rollback(); rollbackErr != nil {
			m.logger.Warn("error rolling back transaction after commit failure", zap.Error(rollbackErr))
		}
		return fmt.Errorf("failed to commit transaction for CreateTable: %w", err)
	}

	return nil
}

// CreateTableFromS3 creates a table in DuckDB by reading data from an S3 path.
func (m *OlapDBDriver) CreateTableFromS3(s3Path, tableName, format string, alterColumnNames map[string]string) error {
	if !strings.HasPrefix(s3Path, "s3://") {
		return fmt.Errorf("invalid S3 path: must start with s3://, got %s", s3Path)
	}

	sb := sqlbuilder.NewSelectBuilder()
	sb.Select("*")

	var readFunc string
	escapedS3Path := sqlbuilder.Escape(s3Path)

	switch format {
	case "parquet":
		readFunc = fmt.Sprintf("read_parquet('%s')", escapedS3Path)
	case "csv":
		readFunc = fmt.Sprintf("read_csv_auto('%s')", escapedS3Path)
	case "json":
		readFunc = fmt.Sprintf("read_json_auto('%s')", escapedS3Path)
	default:
		return fmt.Errorf("unsupported format for CreateTableFromS3: %s", format)
	}
	sb.From(readFunc)

	readSql, readArgs := sb.Build()
	if len(readArgs) > 0 {
		m.logger.Error("unexpected arguments generated for S3 read query", zap.Any("args", readArgs))
		return fmt.Errorf("unexpected arguments in S3 read query construction")
	}

	createSql := fmt.Sprintf(`CREATE OR REPLACE TABLE %s AS (%s)`, sqlbuilder.Escape(tableName), readSql)

	m.logger.Debug("preparing to create table from S3", zap.String("query", createSql))

	tx, err := m.db.BeginTx(context.Background(), nil)
	if err != nil {
		m.logger.Error("error starting transaction for CreateTableFromS3", zap.Error(err))
		return err
	}

	_, err = tx.Exec(createSql)
	if err != nil {
		m.logger.Error("error executing create table from S3 query", zap.String("query", createSql), zap.Error(err))
		if rollbackErr := tx.Rollback(); rollbackErr != nil {
			m.logger.Error("error rolling back transaction after create failure", zap.Error(rollbackErr))
		}
		return parseError(fmt.Errorf("failed creating table '%s' from S3: %w", tableName, err))
	}
	m.logger.Info("successfully created/replaced table from S3", zap.String("tableName", tableName), zap.String("s3Path", s3Path))

	if alterColumnNames != nil && len(alterColumnNames) > 0 {
		m.logger.Debug("renaming columns", zap.String("tableName", tableName), zap.Int("count", len(alterColumnNames)))
		escapedTableName := sqlbuilder.Escape(tableName)
		for key, value := range alterColumnNames {
			escapedOldCol := sqlbuilder.Escape(key)
			escapedNewCol := sqlbuilder.Escape(value)

			alterSql := fmt.Sprintf(`ALTER TABLE %s RENAME COLUMN "%s" TO "%s"`, escapedTableName, escapedOldCol, escapedNewCol)
			m.logger.Debug("executing alter query", zap.String("query", alterSql))

			_, err = tx.Exec(alterSql)
			if err != nil {
				m.logger.Error("error executing alter column query", zap.String("query", alterSql), zap.Error(err))
				if rollbackErr := tx.Rollback(); rollbackErr != nil {
					m.logger.Error("error rolling back transaction after alter failure", zap.Error(rollbackErr))
				}
				return parseError(fmt.Errorf("failed renaming column '%s' to '%s' in table '%s': %w", key, value, tableName, err))
			}
		}
		m.logger.Info("successfully renamed columns", zap.String("tableName", tableName))
	}

	if err = tx.Commit(); err != nil {
		m.logger.Error("error committing transaction for CreateTableFromS3", zap.Error(err))
		if rollbackErr := tx.Rollback(); rollbackErr != nil {
			m.logger.Warn("error rolling back transaction after commit failure", zap.Error(rollbackErr))
		}
		return fmt.Errorf("failed to commit transaction for CreateTableFromS3: %w", err)
	}

	return nil
}

// Query executes a given SQL query string against the database.
func (m *OlapDBDriver) Query(query string) (*models.Result, error) {
	queryID, _ := uuid.NewV7()
	start := time.Now()
	m.logger.Debug("executing user query", zap.String("query ID", queryID.String()), zap.String("query", query))

	rows, err := m.db.Query(query)
	latencyInMs := time.Since(start).Milliseconds()

	if err != nil {
		m.logger.Error("error executing query",
			zap.String("query ID", queryID.String()),
			zap.String("query", query),
			zap.Int64("latency_ms", latencyInMs),
			zap.Error(err))
		return nil, parseError(err)
	}

	m.logger.Info("query executed successfully",
		zap.String("query ID", queryID.String()),
		zap.Int64("latency_ms", latencyInMs))

	result := models.Result{
		Rows: rows,
	}

	return &result, nil
}

func (m *OlapDBDriver) DropTable(tableName string) error {
	escapedTableName := sqlbuilder.Escape(tableName)
	sql := fmt.Sprintf("DROP TABLE IF EXISTS %s", escapedTableName) // Use IF EXISTS for idempotency
	m.logger.Debug("executing drop table query", zap.String("query", sql))

	_, err := m.db.Exec(sql)
	if err != nil {
		m.logger.Error("error dropping table", zap.String("tableName", tableName), zap.Error(err))
		return parseError(fmt.Errorf("failed dropping table '%s': %w", tableName, err))
	}

	m.logger.Info("successfully dropped table", zap.String("tableName", tableName))
	return nil
}

// CreateTableFromPostgres creates a table in DuckDB by executing a query on a Postgres database
func (m *OlapDBDriver) CreateTableFromPostgres(connectionString, sqlQuery, tableName string) error {
	// TODO
	return nil
}

func parseError(err error) error {
	if err == nil {
		return nil
	}

	var duckErr *duckdb.Error
	if errors.As(err, &duckErr) {
		errorTypeMsg := fmt.Sprintf("DuckDB %v error", duckErr.Type)
		return fmt.Errorf("%s: %w", errorTypeMsg, err)
	}
	return err
}

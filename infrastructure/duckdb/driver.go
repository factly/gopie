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
	"github.com/marcboeker/go-duckdb"
	_ "github.com/marcboeker/go-duckdb"
	"go.uber.org/zap"
)

type OlapDBDriver struct {
	db     *sql.DB
	logger *logger.Logger
}

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

	if cfg.DB == "duckdb" {
		err = olap.postDuckDbConnect(s3Cfg)
		if err != nil {
			logger.Error("failed to run post-connection setup",
				zap.String("db_type", cfg.DB),
				zap.Error(err))
			return nil, err
		}
		logger.Info("completed post-connection setup successfully")
	}
	return &olap, nil
}

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
		return err
	}

	m.db = db
	return nil
}

func (m *OlapDBDriver) postDuckDbConnect(s3Cfg *config.S3Config) error {
	m.logger.Debug("starting post-connection setup")

	_, err := m.db.Exec("install httpfs;")
	if err != nil {
		m.logger.Error("failed to install httpfs extension",
			zap.Error(err))
		return fmt.Errorf("error installing httpfs extension: %w", err)
	}
	m.logger.Debug("httpfs extension installed")

	_, err = m.db.Exec("load httpfs;")
	if err != nil {
		m.logger.Error("failed to load httpfs extension",
			zap.Error(err))
		return fmt.Errorf("error loading httpfs extension: %w", err)
	}
	m.logger.Debug("httpfs extension loaded")

	_, err = m.db.Exec(fmt.Sprintf(("SET s3_access_key_id='%s';"), s3Cfg.AccessKey))
	if err != nil {
		m.logger.Error("failed to set S3 access key",
			zap.Error(err))
		return fmt.Errorf("error setting s3 access key: %w", err)
	}
	m.logger.Debug("S3 access key configured")

	_, err = m.db.Exec(fmt.Sprintf("SET s3_secret_access_key='%s';", s3Cfg.SecretKey))
	if err != nil {
		m.logger.Error("failed to set S3 secret key",
			zap.Error(err))
		return fmt.Errorf("failed to set S3 secret key: %w", err)
	}
	m.logger.Debug("S3 secret key configured")

	if s3Cfg.Endpoint != "" {
		_, err = m.db.Exec(fmt.Sprintf("SET s3_endpoint='%s';", s3Cfg.Endpoint))
		if err != nil {
			m.logger.Error("failed to set S3 endpoint",
				zap.String("endpoint", s3Cfg.Endpoint),
				zap.Error(err))
			return fmt.Errorf("failed to set S3 endpoint: %w", err)
		}
		m.logger.Debug("S3 endpoint configured",
			zap.String("endpoint", s3Cfg.Endpoint))
	}

	if s3Cfg.Region != "" {
		_, err = m.db.Exec(fmt.Sprintf("SET s3_region='%s';", s3Cfg.Region))
		if err != nil {
			m.logger.Error("failed to set S3 region",
				zap.String("region", s3Cfg.Region),
				zap.Error(err))
			return fmt.Errorf("failed to set S3 region: %w", err)
		}
		m.logger.Debug("S3 region configured",
			zap.String("region", s3Cfg.Region))
	}

	_, err = m.db.Exec("SET s3_url_style='path';")
	if err != nil {
		m.logger.Error("failed to set S3 URL style",
			zap.Error(err))
		return fmt.Errorf("failed to set S3 URL style: %w", err)
	}
	m.logger.Debug("S3 URL style configured")

	_, err = m.db.Exec(fmt.Sprintf("SET s3_use_ssl=%v;", s3Cfg.SSL))
	if err != nil {
		m.logger.Error("failed to set S3 SSL config",
			zap.Error(err))
		return fmt.Errorf("failed to set S3 SSL config: %w", err)
	}

	m.logger.Info("S3 configuration completed successfully",
		zap.String("endpoint", s3Cfg.Endpoint),
		zap.String("region", s3Cfg.Region))

	return nil
}

func (m *OlapDBDriver) Close() error {
	if m.db != nil {
		return m.db.Close()
	}
	return nil
}

func (m *OlapDBDriver) CreateTable(filePath, tableName, format string, alterColumnNames map[string]string) error {
	readSql := ""
	switch format {
	case "parquet":
		readSql = fmt.Sprintf("select * from read_parquet('%s')", filePath)
		break
	case "csv":
		readSql = fmt.Sprintf("select * from read_csv('%s')", filePath)
		break
	case "json":
		readSql = fmt.Sprintf("select * from read_json('%s')", filePath)
		break
	default:
		return fmt.Errorf("unsupported format: %s", format)
	}

	sql := fmt.Sprintf(`CREATE OR REPLACE TABLE "%s" AS (%s)`, tableName, readSql)

	tx, err := m.db.BeginTx(context.Background(), nil)

	if err != nil {
		m.logger.Error("error starting transaction", zap.Error(err))
		return err
	}
	_, err = tx.Exec(sql)

	if err != nil {
		m.logger.Error("error executing query", zap.String("query", sql), zap.Error(err))
		if rollbackErr := tx.Rollback(); rollbackErr != nil {
			m.logger.Error("error rolling back transaction", zap.Error(rollbackErr))
		}
		return err
	}

	if alterColumnNames != nil {
		for key, value := range alterColumnNames {
			alterSql := fmt.Sprintf(`ALTER TABLE %s RENAME COLUMN "%s" TO "%s"`, tableName, key, value)
			_, err = tx.Exec(alterSql)
			if err != nil {
				m.logger.Error("error executing alter query", zap.String("query", alterSql), zap.Error(err))
				if rollbackErr := tx.Rollback(); rollbackErr != nil {
					m.logger.Error("error rolling back transaction", zap.Error(rollbackErr))
				}
				return err
			}
		}
	}

	if err = tx.Commit(); err != nil {
		m.logger.Error("error committing transaction", zap.Error(err))
		if rollbackErr := tx.Rollback(); rollbackErr != nil {
			m.logger.Error("error rolling back transaction", zap.Error(rollbackErr))
		}
		return err
	}

	return nil
}

func (m *OlapDBDriver) CreateTableFromS3(s3Path, tableName, format string, alterColumnNames map[string]string) error {
	// Parse S3 path
	if !strings.HasPrefix(s3Path, "s3://") {
		return fmt.Errorf("invalid S3 path: must start with s3://")
	}

	readSql := ""
	switch format {
	case "parquet":
		readSql = fmt.Sprintf("SELECT * FROM read_parquet('%s')", s3Path)
	case "csv":
		readSql = fmt.Sprintf("SELECT * FROM read_csv('%s')", s3Path)
	case "json":
		readSql = fmt.Sprintf("SELECT * FROM read_json('%s')", s3Path)
	default:
		return fmt.Errorf("unsupported format: %s", format)
	}

	sql := fmt.Sprintf(`CREATE OR REPLACE TABLE "%s" AS (%s)`, tableName, readSql)
	tx, err := m.db.BeginTx(context.Background(), nil)

	if err != nil {
		m.logger.Error("error starting transaction", zap.Error(err))
		return err
	}
	_, err = tx.Exec(sql)
	if err != nil {
		m.logger.Error("error executing query", zap.String("query", sql), zap.Error(err))
		if rollbackErr := tx.Rollback(); rollbackErr != nil {
			m.logger.Error("error rolling back transaction", zap.Error(rollbackErr))
		}
		return err
	}

	if alterColumnNames != nil {
		for key, value := range alterColumnNames {
			alterSql := fmt.Sprintf(`ALTER TABLE %s RENAME COLUMN "%s" TO "%s"`, tableName, key, value)
			_, err = tx.Exec(alterSql)
			if err != nil {
				m.logger.Error("error executing alter query", zap.String("query", alterSql), zap.Error(err))
				if rollbackErr := tx.Rollback(); rollbackErr != nil {
					m.logger.Error("error rolling back transaction", zap.Error(rollbackErr))
				}
				return err
			}
		}
	}
	if err = tx.Commit(); err != nil {
		m.logger.Error("error committing transaction", zap.Error(err))
		if rollbackErr := tx.Rollback(); rollbackErr != nil {
			m.logger.Error("error rolling back transaction", zap.Error(rollbackErr))
		}
		return err
	}

	return nil
}

func (m *OlapDBDriver) Query(query string) (*models.Result, error) {
	uuid, _ := uuid.NewV7()
	start := time.Now()
	rows, err := m.db.Query(query)
	if err != nil {
		m.logger.Error("error querying motherduck", zap.Error(err))
		return nil, parseError(err)
	}
	latencyInMs := time.Since(start).Milliseconds()
	m.logger.Debug("query executed", zap.String("query ID", uuid.String()), zap.String("query", query), zap.Int64("latency in ms", latencyInMs))

	result := models.Result{
		Rows: rows,
	}

	return &result, nil
}

func (m *OlapDBDriver) DropTable(tableName string) error {
	sql := fmt.Sprintf("DROP TABLE %s", tableName)

	_, err := m.db.Exec(sql)

	return err
}

func parseError(err error) error {
	var duckErr *duckdb.Error
	if errors.As(err, &duckErr) {
		switch duckErr.Type {
		case duckdb.ErrorTypeCatalog:
			return fmt.Errorf("DuckDB catalog error: %w", err)
		case duckdb.ErrorTypeBinder:
			return fmt.Errorf("DuckDB binding error (e.g. column not found): %w", err)
		case duckdb.ErrorTypeParser:
			return fmt.Errorf("DuckDB syntax error: %w", err)
		case duckdb.ErrorTypeConstraint:
			return fmt.Errorf("DuckDB constraint violation: %w", err)
		case duckdb.ErrorTypeConversion:
			return fmt.Errorf("DuckDB type conversion error: %w", err)
		case duckdb.ErrorTypeInvalidInput:
			return fmt.Errorf("DuckDB invalid input: %w", err)
		case duckdb.ErrorTypeConnection:
			return fmt.Errorf("DuckDB connection error: %w", err)
		}
	}
	return err
}

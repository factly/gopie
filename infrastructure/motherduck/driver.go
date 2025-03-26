package motherduck

import (
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
	logger.Info("connecting to motherduck")
	err := olap.Connect(cfg)
	if err != nil {
		logger.Error("error connecting to motherduck", zap.Error(err))
		fmt.Println("error connecting to motherduck: ", err.Error())
		return nil, err
	}
	logger.Info("connected to motherduck")
	if cfg.DBType == "duck" {
		err = olap.postDuckDbConnect(s3Cfg)
		if err != nil {
			logger.Error("error connecting to motherduck", zap.Error(err))
			fmt.Println("error connecting to motherduck: ", err.Error())
			return nil, err
		}
		logger.Info("post duckdb connection successful")
	}
	return &olap, nil
}

func (m *OlapDBDriver) Connect(cfg *config.OlapDBConfig) error {

	var dsn string
	if cfg.DBType == "motherduck" {
		dsn = fmt.Sprintf("md:%s?motherduck_token=%s", cfg.MotherDuck.DBName, cfg.MotherDuck.Token)
		if cfg.AccessMode != "" {
			dsn = fmt.Sprintf("%s&access_mode=%s", dsn, cfg.AccessMode)
			m.logger.Info("access mode", zap.String("mode", cfg.AccessMode))
		}
	} else {
		dsn = cfg.DuckDB.Path

		params := []string{}

		if cfg.DuckDB.CPU > 0 {
			params = append(params, fmt.Sprintf("threads=%d", cfg.DuckDB.CPU))
		}

		if cfg.DuckDB.MemoryLimit > 0 {
			params = append(params, fmt.Sprintf("memory_limit=%dMB", cfg.DuckDB.MemoryLimit))
		}

		if cfg.AccessMode != "" {
			params = append(params, fmt.Sprintf("access_mode=%s", cfg.AccessMode))
		}

		// Add query parameters if we have any
		if len(params) > 0 {
			dsn = fmt.Sprintf("%s?%s", dsn, strings.Join(params, "&"))
		}

		m.logger.Info("duckdb connection string", zap.String("dsn", dsn))
	}

	db, err := sql.Open("duckdb", dsn)
	if err != nil {
		m.logger.Error("error connecting to motherduck", zap.Error(err))
		return err
	}

	m.db = db
	return nil
}

func (m *OlapDBDriver) postDuckDbConnect(s3Cfg *config.S3Config) error {
	_, err := m.db.Exec("install httpfs;")
	if err != nil {
		m.logger.Error("error installing httpfs", zap.Error(err))
		return fmt.Errorf("error installing httpfs extension: %w", err)
	}

	_, err = m.db.Exec("load httpfs;")
	if err != nil {
		m.logger.Error("error loading httpfs", zap.Error(err))
		return fmt.Errorf("error loading httpfs extension: %w", err)
	}

	// Set S3 credentials
	_, err = m.db.Exec(fmt.Sprintf(("SET s3_access_key_id='%s';"), s3Cfg.AccessKey))
	if err != nil {
		m.logger.Error("error setting s3 access key", zap.Error(err))
		return fmt.Errorf("error setting s3 access key: %w", err)
	}

	_, err = m.db.Exec(fmt.Sprintf("SET s3_secret_access_key='%s';", s3Cfg.SecretKey))
	if err != nil {
		m.logger.Error("error setting S3 secret key", zap.Error(err))
		return fmt.Errorf("failed to set S3 secret key: %w", err)
	}

	if s3Cfg.Endpoint != "" {
		_, err = m.db.Exec(fmt.Sprintf("SET s3_endpoint='%s';", s3Cfg.Endpoint))
		if err != nil {
			m.logger.Error("error setting S3 endpoint", zap.Error(err))
			return fmt.Errorf("failed to set S3 endpoint: %w", err)
		}
	}

	if s3Cfg.Region != "" {
		_, err = m.db.Exec(fmt.Sprintf("SET s3_region='%s';", s3Cfg.Region))
		if err != nil {
			m.logger.Error("error setting S3 region", zap.Error(err))
			return fmt.Errorf("failed to set S3 region: %w", err)
		}
	}

	_, err = m.db.Exec("SET s3_url_style='path';")
	if err != nil {
		m.logger.Error("error setting S3 URL style", zap.Error(err))
		return fmt.Errorf("failed to set S3 URL style: %w", err)
	}

	_, err = m.db.Exec("SET s3_use_ssl=false;")
	if err != nil {
		m.logger.Error("error disabling S3 SSL", zap.Error(err))
		return fmt.Errorf("failed to disable S3 SSL: %w", err)
	}

	m.logger.Info("S3 configuration successful",
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

func (m *OlapDBDriver) CreateTable(filePath, tableName, format string) error {
	readSql := ""
	switch format {
	case "parquet":
		readSql = fmt.Sprintf("select * from read_parquet('%s')", filePath)
		break
	case "csv":
		readSql = fmt.Sprintf("select * from read_csv('%s')", filePath)
		break
	case "json":
		readSql = fmt.Sprintf("select * read_json('%s')", filePath)
		break
	default:
		return fmt.Errorf("unsupported format: %s", format)
	}

	sql := fmt.Sprintf(`CREATE OR REPLACE TABLE "%s" AS (%s)`, tableName, readSql)

	_, err := m.db.Exec(sql)

	return err
}

func (m *OlapDBDriver) CreateTableFromS3(s3Path, tableName, format string) error {
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
	_, err := m.db.Exec(sql)
	return err
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

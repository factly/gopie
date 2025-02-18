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

type motherDuckOlapoDriver struct {
	db     *sql.DB
	logger *logger.Logger
}

func NewMotherDuckOlapoDriver(cfg *config.MotherDuckConfig, logger *logger.Logger) (repositories.OlapRepository, error) {
	olap := motherDuckOlapoDriver{
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
	return &olap, nil
}

func (m *motherDuckOlapoDriver) Connect(cfg *config.MotherDuckConfig) error {
	dsn := fmt.Sprintf("md:%s?motherduck_token=%s", cfg.DBName, cfg.Token)
	if cfg.AccessMode != "" {
		dsn = fmt.Sprintf("%s&access_mode=%s", dsn, cfg.AccessMode)
		m.logger.Info("access mode", zap.String("mode", cfg.AccessMode))
	}

	db, err := sql.Open("duckdb", dsn)
	if err != nil {
		m.logger.Error("error connecting to motherduck", zap.Error(err))
		return err
	}

	m.db = db
	return nil
}

func (m *motherDuckOlapoDriver) Close() error {
	if m.db != nil {
		return m.db.Close()
	}
	return nil
}

func (m *motherDuckOlapoDriver) CreateTable(filePath, tableName, format string) error {
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

func (m *motherDuckOlapoDriver) CreateTableFromS3(s3Path, tableName, format string) error {
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

func (m *motherDuckOlapoDriver) Query(query string) (*models.Result, error) {
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

func (m *motherDuckOlapoDriver) DropTable(tableName string) error {
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

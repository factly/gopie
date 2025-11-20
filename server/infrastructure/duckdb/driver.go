package duckdb

import (
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"go.uber.org/zap"
)

// OlapDBDriver implements the repositories.OlapRepository interface for DuckDB/MotherDuck.
type OlapDBDriver struct {
	db       *sql.DB
	logger   *logger.Logger
	olapType string // "duckdb" or "motherduck"
	dbName   string
	// Only used for MotherDuck
	helperDB *sql.DB
	// S3 configuration to reapply for each S3 operation
	s3Config *config.S3Config
}

// NewOlapDBDriver initializes a new DuckDB/MotherDuck driver.
func NewOlapDBDriver(cfg *config.OlapDBConfig, logger *logger.Logger, s3Cfg *config.S3Config) (repositories.OlapRepository, error) {
	olap := OlapDBDriver{
		logger:   logger,
		s3Config: s3Cfg, // Store S3 config for later use
	}
	logger.Info("initializing duckdb driver",
		zap.String("db_type", cfg.DB),
		zap.String("access_mode", cfg.AccessMode))

	err := olap.Connect(cfg)
	if err != nil {
		logger.Critical("failed to connect to duckdb",
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

// Connect establishes the database connection.
func (m *OlapDBDriver) Connect(cfg *config.OlapDBConfig) error {
	dsn, err := m.buildDSN(cfg)
	if err != nil {
		return err // Error already logged in buildDSN or is a config error
	}

	if cfg.DB == "motherduck" && cfg.AccessMode != "read_only" {
		helperDBFileName := fmt.Sprintf("gopie_%s.db", pkg.RandomString(10))
		helperDBPath := filepath.Join(cfg.MotherDuck.HelperDBDirPath, helperDBFileName)

		// Ensure the directory exists before creating the helper DB file
		if err := os.MkdirAll(cfg.MotherDuck.HelperDBDirPath, 0755); err != nil {
			m.logger.Error("failed to create helper DB directory",
				zap.String("directory", cfg.MotherDuck.HelperDBDirPath),
				zap.Error(err))
			return fmt.Errorf("failed to create helper DB directory: %w", err)
		}

		m.helperDB, err = m.connectToMotherDuckHelperDB(helperDBPath, fmt.Sprintf("md:%s", cfg.MotherDuck.DBName), cfg.MotherDuck.Token)
		if err != nil {
			return err
		}
	}

	db, err := sql.Open("duckdb", dsn)
	if err != nil {
		m.logger.Error("failed to open database connection",
			zap.String("db_type", cfg.DB),
			zap.Error(err))
		return err
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

// buildDSN constructs the DSN string for DuckDB or MotherDuck.
func (m *OlapDBDriver) buildDSN(cfg *config.OlapDBConfig) (string, error) {
	if cfg.DB == "motherduck" {
		m.olapType = "motherduck"
		if cfg.MotherDuck.DBName == "" || cfg.MotherDuck.Token == "" {
			m.logger.Error("motherduck configuration incomplete",
				zap.Bool("db_name_missing", cfg.MotherDuck.DBName == ""),
				zap.Bool("token_missing", cfg.MotherDuck.Token == ""))
			return "", errors.New("motherduck DBName and Token are required")
		}
		dsn := fmt.Sprintf("md:%s?motherduck_token=%s", cfg.MotherDuck.DBName, cfg.MotherDuck.Token)
		if cfg.AccessMode != "" {
			dsn = fmt.Sprintf("%s&access_mode=%s", dsn, cfg.AccessMode)
			m.logger.Debug("setting motherduck access mode", zap.String("mode", cfg.AccessMode))
		}
		return dsn, nil
	}

	m.olapType = "duckdb"
	dsn := cfg.DuckDB.Path
	params := []string{}

	if cfg.DuckDB.CPU > 0 {
		params = append(params, fmt.Sprintf("threads=%d", cfg.DuckDB.CPU))
		m.logger.Debug("setting CPU threads", zap.Int("threads", cfg.DuckDB.CPU))
	}
	if cfg.DuckDB.MemoryLimit > 0 {
		params = append(params, fmt.Sprintf("memory_limit=%dMB", cfg.DuckDB.MemoryLimit))
		m.logger.Debug("setting memory limit", zap.Int("limit_mb", cfg.DuckDB.MemoryLimit))
	}
	if cfg.AccessMode != "" {
		params = append(params, fmt.Sprintf("access_mode=%s", cfg.AccessMode))
		m.logger.Debug("setting duckdb access mode", zap.String("mode", cfg.AccessMode))
	}

	if len(params) > 0 {
		dsn = fmt.Sprintf("%s?%s", dsn, strings.Join(params, "&"))
	}
	m.logger.Debug("constructed duckdb connection string", zap.String("dsn", dsn))
	return dsn, nil
}

// connectToMotherDuckHelperDB connects to and initializes the helper DB for MotherDuck.
func (m *OlapDBDriver) connectToMotherDuckHelperDB(helperDSN, motherduckDsn, motherduckToken string) (*sql.DB, error) {
	m.logger.Debug("connecting to motherduck helper database", zap.String("dsn", helperDSN))
	helperDB, err := sql.Open("duckdb", helperDSN)
	if err != nil {
		m.logger.Error("failed to connect to motherduck helper database", zap.String("dsn", helperDSN), zap.Error(err))
		return nil, fmt.Errorf("failed to connect to motherduck helper database: %w", err)
	}

	if err := helperDB.Ping(); err != nil {
		helperDB.Close()
		m.logger.Error("failed to ping motherduck helper database", zap.String("dsn", helperDSN), zap.Error(err))
		return nil, fmt.Errorf("failed to ping motherduck helper database: %w", err)
	}

	commands := []string{
		"INSTALL postgres;", "LOAD postgres;",
		"INSTALL mysql;", "LOAD mysql;",
		"INSTALL motherduck;", "LOAD motherduck;",
		fmt.Sprintf(`SET motherduck_token='%s';`, motherduckToken),
		fmt.Sprintf("ATTACH '%s'", motherduckDsn),
	}

	for i, cmd := range commands {
		logFields := []zap.Field{zap.String("command_index", fmt.Sprintf("%d/%d", i+1, len(commands)))}
		if i == 6 { // This is the SET motherduck_token command
			logFields = append(logFields, zap.String("command", "SET motherduck_token='REDACTED'"))
		} else {
			logFields = append(logFields, zap.String("command", cmd))
		}
		m.logger.Debug("executing command on motherduck helper db", logFields...)

		_, err := helperDB.Exec(cmd)
		if err != nil {
			helperDB.Close()
			m.logger.Error("error initializing motherduck helper db", zap.String("command", cmd), zap.Error(err))
			return nil, fmt.Errorf("error initializing motherduck helper db: failed to execute command '%s': %w", cmd, err)
		}
	}

	m.logger.Info("connected to and initialized motherduck helper db", zap.String("helper_db_path", helperDSN))
	return helperDB, nil
}

// Close closes the database connection(s).
func (m *OlapDBDriver) Close() error {
	var firstErr error
	if m.db != nil {
		m.logger.Info("closing main duckdb connection")
		if err := m.db.Close(); err != nil {
			m.logger.Error("error closing main duckdb connection", zap.Error(err))
			firstErr = err
		}
	}
	if m.helperDB != nil {
		m.logger.Info("closing motherduck helper db connection")
		if err := m.helperDB.Close(); err != nil {
			m.logger.Error("error closing motherduck helper db connection", zap.Error(err))
			if firstErr == nil {
				firstErr = err
			}
		}
	}
	return firstErr
}

// GetDB returns the main database connection.
func (m *OlapDBDriver) GetDB() any {
	return m.db
}

// GetHelperDB returns the appropriate database connection based on OLAP type.
func (m *OlapDBDriver) GetHelperDB() any {
	switch m.olapType {
	case "duckdb":
		return m.db
	case "motherduck":
		return m.helperDB
	}
	return nil
}

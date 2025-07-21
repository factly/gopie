package duckdb

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/google/uuid"
	"github.com/huandu/go-sqlbuilder"
	"github.com/marcboeker/go-duckdb"
	_ "github.com/marcboeker/go-duckdb" // DB driver
	pg_query "github.com/pganalyze/pg_query_go/v6"
	"go.uber.org/zap"
	"vitess.io/vitess/go/vt/sqlparser"
)

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

// generateS3Commands generates only the S3-specific commands for applying to transactions
func (m *OlapDBDriver) generateS3Commands(s3Cfg *config.S3Config) []string {
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

	return s3Commands
}

// applyS3SettingsToTransaction applies S3 settings within a transaction context
func (m *OlapDBDriver) applyS3SettingsToTransaction(tx *sql.Tx) error {
	if m.s3Config == nil {
		return nil // No S3 config to apply
	}

	s3Commands := m.generateS3Commands(m.s3Config)
	for _, cmd := range s3Commands {
		m.logger.Debug("reapplying S3 setting in transaction", zap.String("command", cmd))
		if _, err := tx.Exec(cmd); err != nil {
			m.logger.Error("failed to reapply S3 setting in transaction",
				zap.String("command", cmd),
				zap.Error(err))
			return fmt.Errorf("failed reapplying S3 setting '%s': %w", cmd, err)
		}
	}
	return nil
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

// buildReadFunctionSQL constructs the SQL function part for reading data (e.g., read_parquet(...)).
func (m *OlapDBDriver) buildReadFunctionSQL(escapedPath, format string) (string, error) {
	switch format {
	case "parquet":
		return fmt.Sprintf("read_parquet('%s')", escapedPath), nil
	case "csv":
		return fmt.Sprintf("read_csv_auto('%s')", escapedPath), nil
	case "json":
		return fmt.Sprintf("read_json_auto('%s')", escapedPath), nil
	default:
		return "", fmt.Errorf("unsupported format for table creation: %s", format)
	}
}

// renameTableColumns executes ALTER TABLE RENAME COLUMN commands within a transaction.
func (m *OlapDBDriver) renameTableColumns(tx *sql.Tx, tableName string, alterColumnNames map[string]string, logger *logger.Logger) error {
	if len(alterColumnNames) == 0 {
		return nil
	}

	logger.Debug("renaming columns", zap.String("tableName", tableName), zap.Int("count", len(alterColumnNames)))
	escapedTableName := sqlbuilder.Escape(tableName)

	for oldName, newName := range alterColumnNames {
		escapedOldCol := sqlbuilder.Escape(oldName)
		escapedNewCol := sqlbuilder.Escape(newName)

		alterSql := fmt.Sprintf(`ALTER TABLE %s RENAME COLUMN "%s" TO "%s"`, escapedTableName, escapedOldCol, escapedNewCol)
		logger.Debug("executing alter column query", zap.String("query", alterSql))

		_, err := tx.Exec(alterSql)
		if err != nil {
			logger.Error("error executing alter column query", zap.String("query", alterSql), zap.Error(err))
			return parseError(fmt.Errorf("failed renaming column '%s' to '%s' in table '%s': %w", oldName, newName, tableName, err))
		}
	}
	logger.Info("successfully renamed columns", zap.String("tableName", tableName))
	return nil
}

// createTableInternal is the shared logic for CreateTable and CreateTableFromS3.
func (m *OlapDBDriver) createTableInternal(sourcePath, tableName, format string, alterColumnNames map[string]string, isS3 bool) error {
	dataSourceType := "file"
	if isS3 {
		dataSourceType = "S3"
		if !strings.HasPrefix(sourcePath, "s3://") {
			return fmt.Errorf("invalid S3 path: must start with s3://, got %s", sourcePath)
		}
	}

	escapedPath := sqlbuilder.Escape(sourcePath)
	readFunc, err := m.buildReadFunctionSQL(escapedPath, format)
	if err != nil {
		m.logger.Error("failed to build read function for table creation", zap.String("format", format), zap.Error(err))
		return err
	}

	// Using SelectBuilder for the read part of "CREATE TABLE AS SELECT..."
	sb := sqlbuilder.NewSelectBuilder()
	sb.Select("*").From(readFunc)
	readSql, readArgs := sb.Build()

	if len(readArgs) > 0 {
		m.logger.Error("unexpected arguments generated for read query in table creation", zap.Any("args", readArgs))
		return fmt.Errorf("unexpected arguments in read query construction for table creation")
	}

	createSql := fmt.Sprintf(`CREATE OR REPLACE TABLE %s AS (%s)`, sqlbuilder.Escape(tableName), readSql)
	m.logger.Debug(fmt.Sprintf("preparing to create table from %s", dataSourceType), zap.String("query", createSql))

	tx, err := m.db.BeginTx(context.Background(), nil)
	if err != nil {
		m.logger.Error(fmt.Sprintf("error starting transaction for CreateTableFrom%s", dataSourceType), zap.Error(err))
		return err
	}
	defer tx.Rollback() // Ensure rollback on error or panic if commit isn't reached

	// Apply S3 settings to the transaction if this is an S3 operation
	if isS3 && m.olapType == "duckdb" {
		m.logger.Debug("applying S3 settings to transaction for S3 operation")
		if err := m.applyS3SettingsToTransaction(tx); err != nil {
			m.logger.Error("failed to apply S3 settings to transaction", zap.Error(err))
			return fmt.Errorf("failed to apply S3 settings to transaction: %w", err)
		}
	}

	_, err = tx.Exec(createSql)
	if err != nil {
		m.logger.Error(fmt.Sprintf("error executing create table from %s query", dataSourceType), zap.String("query", createSql), zap.Error(err))
		return parseError(fmt.Errorf("failed creating table '%s' from %s: %w", tableName, dataSourceType, err))
	}
	m.logger.Info(fmt.Sprintf("successfully created/replaced table from %s", dataSourceType), zap.String("tableName", tableName), zap.String("sourcePath", sourcePath))

	if err = m.renameTableColumns(tx, tableName, alterColumnNames, m.logger); err != nil {
		m.logger.Error(fmt.Sprintf("error renaming columns in table created from %s", dataSourceType), zap.String("tableName", tableName), zap.Error(err))
		return err
	}

	if err = tx.Commit(); err != nil {
		m.logger.Error(fmt.Sprintf("error committing transaction for CreateTableFrom%s", dataSourceType), zap.Error(err))
		return fmt.Errorf("failed to commit transaction for CreateTableFrom%s: %w", dataSourceType, err)
	}

	return nil
}

// CreateTable creates a table in DuckDB by reading data from a local file path.
func (m *OlapDBDriver) CreateTable(filePath, tableName, format string, alterColumnNames map[string]string) error {
	return m.createTableInternal(filePath, tableName, format, alterColumnNames, false)
}

// CreateTableFromS3 creates a table in DuckDB by reading data from an S3 path.
func (m *OlapDBDriver) CreateTableFromS3(s3Path, tableName, format string, alterColumnNames map[string]string) error {
	return m.createTableInternal(s3Path, tableName, format, alterColumnNames, true)
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

// DropTable removes a table from the database if it exists.
func (m *OlapDBDriver) DropTable(tableName string) error {
	escapedTableName := sqlbuilder.Escape(tableName)
	sqlCmd := fmt.Sprintf("DROP TABLE IF EXISTS %s", escapedTableName)
	m.logger.Debug("executing drop table query", zap.String("query", sqlCmd))

	_, err := m.db.Exec(sqlCmd)
	if err != nil {
		m.logger.Error("error dropping table", zap.String("tableName", tableName), zap.Error(err))
		return parseError(fmt.Errorf("failed dropping table '%s': %w", tableName, err))
	}

	m.logger.Info("successfully dropped table", zap.String("tableName", tableName))
	return nil
}

// CreateTableFromPostgres creates a table in DuckDB by executing a query on a Postgres database
func (m *OlapDBDriver) CreateTableFromPostgres(connectionString, sqlQuery, tableName string) error {
	if m.olapType == "motherduck" {
		return m.createTableFromPostgresMotherDuck(connectionString, sqlQuery, tableName)
	} else {
		return m.createTableFromPostgresDuckDB(connectionString, sqlQuery, tableName)
	}
}

func (m *OlapDBDriver) CreateTableFromMySql(connectionString, sqlQuery, tableName string) error {
	if m.olapType == "motherduck" {
		return m.createTableFromMysqlMotherDuck(connectionString, sqlQuery, tableName)
	} else {
		return m.createTableFromMysqlDuckDB(connectionString, sqlQuery, tableName)
	}
}

// parseMySQLConnectionString parses different formats of MySQL connection strings
// into a format compatible with the DuckDB MySQL extension.
func parseMySQLConnectionString(connectionString string) (string, error) {
	// Handle mysql:// protocol format
	if strings.HasPrefix(connectionString, "mysql://") {
		u, err := url.Parse(connectionString)
		if err != nil {
			return "", fmt.Errorf("invalid MySQL connection string: %w", err)
		}

		password, _ := u.User.Password()
		username := u.User.Username()
		host := u.Hostname()
		port := u.Port()
		if port == "" {
			port = "3306" // Default MySQL port
		}

		database := strings.TrimPrefix(u.Path, "/")

		// Construct DuckDB MySQL connection format
		dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s database=%s",
			host, port, username, password, database)

		// Add query parameters if any
		if u.RawQuery != "" {
			params, err := url.ParseQuery(u.RawQuery)
			if err == nil {
				for key, values := range params {
					if len(values) > 0 {
						dsn += fmt.Sprintf(" %s=%s", key, values[0])
					}
				}
			}
		}

		return dsn, nil
	}

	// Handle username:password@tcp(host:port)/database format
	if strings.Contains(connectionString, "@tcp(") {
		// Split by @ to separate credentials and connection info
		parts := strings.SplitN(connectionString, "@", 2)
		if len(parts) != 2 {
			return "", fmt.Errorf("invalid MySQL connection string format")
		}

		credentials := parts[0]
		connInfo := parts[1]

		// Extract username and password
		credParts := strings.SplitN(credentials, ":", 2)
		username := credParts[0]
		password := ""
		if len(credParts) > 1 {
			password = credParts[1]
		}

		// Extract host, port, database
		tcpPart := strings.SplitN(connInfo, ")/", 2)
		if len(tcpPart) != 2 {
			return "", fmt.Errorf("invalid MySQL connection string format")
		}

		hostPort := strings.TrimPrefix(tcpPart[0], "tcp(")
		hostPortParts := strings.SplitN(hostPort, ":", 2)
		host := hostPortParts[0]
		port := "3306"
		if len(hostPortParts) > 1 {
			port = hostPortParts[1]
		}

		// Extract database and parameters
		dbAndParams := strings.SplitN(tcpPart[1], "?", 2)
		database := dbAndParams[0]

		// Construct DuckDB MySQL connection format
		dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s database=%s",
			host, port, username, password, database)

		// Add query parameters if any
		if len(dbAndParams) > 1 {
			params, err := url.ParseQuery(dbAndParams[1])
			if err == nil {
				for key, values := range params {
					if len(values) > 0 {
						dsn += fmt.Sprintf(" %s=%s", key, values[0])
					}
				}
			}
		}

		return dsn, nil
	}

	// Handle username:password@hostname:port/database format
	if strings.Contains(connectionString, "@") && !strings.Contains(connectionString, "://") {
		// Split by @ to separate credentials and connection info
		parts := strings.SplitN(connectionString, "@", 2)
		if len(parts) != 2 {
			return "", fmt.Errorf("invalid MySQL connection string format")
		}

		credentials := parts[0]
		connInfo := parts[1]

		// Extract username and password
		credParts := strings.SplitN(credentials, ":", 2)
		username := credParts[0]
		password := ""
		if len(credParts) > 1 {
			password = credParts[1]
		}

		// Extract host, port, database
		hostPortDB := strings.SplitN(connInfo, "/", 2)
		if len(hostPortDB) != 2 {
			return "", fmt.Errorf("invalid MySQL connection string format")
		}

		hostPort := hostPortDB[0]
		hostPortParts := strings.SplitN(hostPort, ":", 2)
		host := hostPortParts[0]
		port := "3306"
		if len(hostPortParts) > 1 {
			port = hostPortParts[1]
		}

		// Extract database and parameters
		dbAndParams := strings.SplitN(hostPortDB[1], "?", 2)
		database := dbAndParams[0]

		// Construct DuckDB MySQL connection format
		dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s database=%s",
			host, port, username, password, database)

		// Add query parameters if any
		if len(dbAndParams) > 1 {
			params, err := url.ParseQuery(dbAndParams[1])
			if err == nil {
				for key, values := range params {
					if len(values) > 0 {
						dsn += fmt.Sprintf(" %s=%s", key, values[0])
					}
				}
			}
		}

		return dsn, nil
	}

	// Already in key=value format for DuckDB MySQL connection
	if strings.Contains(connectionString, "host=") && strings.Contains(connectionString, "user=") {
		return connectionString, nil
	}

	return "", fmt.Errorf("unsupported MySQL connection string format")
}

func (m *OlapDBDriver) createTableFromPostgresMotherDuck(connectionString, sqlQuery, tableName string) error {
	pgDBAlias := fmt.Sprintf("pg_ext_%s", pkg.RandomString(10))
	parseResult, _ := pg_query.Parse(sqlQuery)
	m.logger.Debug("parsed SQL query", zap.String("query", sqlQuery))
	rawSmt := parseResult.GetStmts()[0]
	stmtNode := rawSmt.GetStmt()
	walkAndQualifyUnqualifiedTablesForPg(stmtNode, pgDBAlias)
	sqlQuery, err := pg_query.Deparse(parseResult)
	if err != nil {
		m.logger.Error("failed to deparse SQL query", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("deparsing SQL query: %w", err)
	}
	m.logger.Debug("deparsed SQL query", zap.String("query", sqlQuery))

	// 1. ATTACH statement
	attachSQL := fmt.Sprintf(`ATTACH '%s' AS "%s" (TYPE POSTGRES)`, connectionString, pgDBAlias) // Quoting alias just in case, though generated ones are usually safe.

	m.logger.Debug("Executing ATTACH SQL", zap.String("alias", pgDBAlias))
	if _, err := m.helperDB.Exec(attachSQL); err != nil {
		m.logger.Error("Failed to attach PostgreSQL database", zap.String("alias", pgDBAlias), zap.Error(err))
		return fmt.Errorf("attaching PostgreSQL database (alias: %s): %w", pgDBAlias, err)
	}
	m.logger.Info("Successfully attached PostgreSQL database", zap.String("alias", pgDBAlias))

	var detachError error
	defer func() {
		// DETACH is also specific
		detachSQLCmd := fmt.Sprintf(`DETACH "%s"`, pgDBAlias) // Quoted alias
		m.logger.Debug("Executing DETACH SQL", zap.String("alias", pgDBAlias), zap.String("sql", detachSQLCmd))
		if _, err := m.helperDB.Exec(detachSQLCmd); err != nil {
			detachError = err
			m.logger.Error("Failed to detach PostgreSQL database", zap.String("alias", pgDBAlias), zap.Error(detachError))
		} else {
			m.logger.Info("Successfully detached PostgreSQL database", zap.String("alias", pgDBAlias))
		}
	}()

	// 2. CREATE TABLE ... AS ... statement
	quotedTargetSchema := fmt.Sprintf("\"%s\"", m.dbName)
	quotedTargetTableName := fmt.Sprintf("\"%s\"", tableName)

	createTableSQL := fmt.Sprintf(`CREATE TABLE IF NOT EXISTS %s.%s AS %s`,
		quotedTargetSchema,
		quotedTargetTableName,
		sqlQuery,
	)

	m.logger.Debug("Executing CREATE TABLE AS SELECT SQL",
		zap.String("target", fmt.Sprintf("%s.%s", m.dbName, tableName)),
		zap.String("sql", createTableSQL),
	)

	_, createErr := m.helperDB.Exec(createTableSQL)
	if createErr != nil {
		m.logger.Error("Failed to create table from PostgreSQL data",
			zap.String("target", fmt.Sprintf("%s.%s", m.dbName, tableName)),
			zap.Error(createErr),
		)
		return fmt.Errorf("creating table %s.%s using SQL query (%s): %w", quotedTargetSchema, quotedTargetTableName, sqlQuery, createErr)
	}

	m.logger.Info("Successfully created table",
		zap.String("target", fmt.Sprintf("%s.%s", m.dbName, tableName)),
	)

	if detachError != nil {
		m.logger.Warn("Table created successfully, but a non-critical error occurred during PostgreSQL detach",
			zap.String("alias", pgDBAlias),
			zap.Error(detachError),
		)
	}

	return nil
}

func (m *OlapDBDriver) createTableFromPostgresDuckDB(connectionString, sqlQuery, tableName string) error {
	pgDBAlias := fmt.Sprintf("pg_ext_%s", pkg.RandomString(10))
	parseResult, _ := pg_query.Parse(sqlQuery)
	m.logger.Debug("parsed SQL query", zap.String("query", sqlQuery))
	rawSmt := parseResult.GetStmts()[0]
	stmtNode := rawSmt.GetStmt()
	walkAndQualifyUnqualifiedTablesForPg(stmtNode, pgDBAlias)
	sqlQuery, err := pg_query.Deparse(parseResult)
	if err != nil {
		m.logger.Error("failed to deparse SQL query", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("deparsing SQL query: %w", err)
	}
	m.logger.Debug("deparsed SQL query", zap.String("query", sqlQuery))
	// 1. ATTACH statement
	attachSQL := fmt.Sprintf(`ATTACH '%s' AS "%s" (TYPE POSTGRES)`, connectionString, pgDBAlias) // Quoting alias just in case, though generated ones are usually safe.

	m.logger.Debug("Executing ATTACH SQL", zap.String("alias", pgDBAlias))
	if _, err := m.db.Exec(attachSQL); err != nil {
		m.logger.Error("Failed to attach PostgreSQL database", zap.String("alias", pgDBAlias), zap.Error(err))
		return fmt.Errorf("attaching PostgreSQL database (alias: %s): %w", pgDBAlias, err)
	}
	m.logger.Info("Successfully attached PostgreSQL database", zap.String("alias", pgDBAlias))

	var detachError error
	defer func() {
		detachSQLCmd := fmt.Sprintf(`DETACH "%s"`, pgDBAlias)
		m.logger.Debug("Executing DETACH SQL", zap.String("alias", pgDBAlias), zap.String("sql", detachSQLCmd))
		if _, err := m.db.Exec(detachSQLCmd); err != nil {
			detachError = err
			m.logger.Error("Failed to detach PostgreSQL database", zap.String("alias", pgDBAlias), zap.Error(detachError))
		} else {
			m.logger.Info("Successfully detached PostgreSQL database", zap.String("alias", pgDBAlias))
		}
	}()

	// 2. CREATE TABLE ... AS ... statement
	quotedTargetTableName := fmt.Sprintf("\"%s\"", tableName)

	createTableSQL := fmt.Sprintf(`CREATE TABLE IF NOT EXISTS %s AS %s`,
		quotedTargetTableName,
		sqlQuery,
	)

	m.logger.Debug("Executing CREATE TABLE AS SELECT SQL",
		zap.String("target", fmt.Sprintf("%s.%s", m.dbName, tableName)),
		zap.String("sql", createTableSQL),
	)

	_, createErr := m.db.Exec(createTableSQL)
	if createErr != nil {
		m.logger.Error("Failed to create table from PostgreSQL data",
			zap.String("target", fmt.Sprintf("%s.%s", m.dbName, tableName)),
			zap.Error(createErr),
		)
		return fmt.Errorf("creating table %s using SQL query (%s): %w", quotedTargetTableName, sqlQuery, createErr)
	}

	m.logger.Info("Successfully created table",
		zap.String("target", fmt.Sprintf("%s.%s", m.dbName, tableName)),
	)

	if detachError != nil {
		m.logger.Warn("Table created successfully, but a non-critical error occurred during PostgreSQL detach",
			zap.String("alias", pgDBAlias),
			zap.Error(detachError),
		)
	}

	return nil
}

func (m *OlapDBDriver) createTableFromMysqlMotherDuck(connectionString, sqlQuery, tableName string) error {
	mySQLDBAlias := fmt.Sprintf("ysql_ext_%s", pkg.RandomString(10))
	parser, _ := sqlparser.New(sqlparser.Options{})
	parseResult, _ := parser.Parse(sqlQuery)
	node := parseResult.(*sqlparser.Select)
	WalkAndQualifyUnqualifiedTablesForMySQL(node, mySQLDBAlias)
	sqlQuery = sqlparser.String(node)

	// Parse the connection string into DuckDB MySQL format
	parsedConnectionString, err := parseMySQLConnectionString(connectionString)
	if err != nil {
		m.logger.Error("Failed to parse MySQL connection string", zap.Error(err))
		return fmt.Errorf("parsing MySQL connection string: %w", err)
	}

	// Mask password for logging
	logConnectionFormat := maskPasswordInConnectionString(parsedConnectionString)

	// 1. ATTACH statement for MySQL
	attachSQL := fmt.Sprintf(`ATTACH '%s' AS "%s" (TYPE MYSQL)`, parsedConnectionString, mySQLDBAlias)

	m.logger.Debug("Executing ATTACH SQL for MySQL",
		zap.String("alias", mySQLDBAlias),
		zap.String("connection_format", logConnectionFormat))
	if _, err := m.helperDB.Exec(attachSQL); err != nil {
		m.logger.Error("Failed to attach MySQL database", zap.String("alias", mySQLDBAlias), zap.Error(err))
		return fmt.Errorf("attaching MySQL database (alias: %s): %w", mySQLDBAlias, err)
	}
	m.logger.Info("Successfully attached MySQL database", zap.String("alias", mySQLDBAlias))

	var detachError error
	defer func() {
		detachSQLCmd := fmt.Sprintf(`DETACH "%s"`, mySQLDBAlias)
		m.logger.Debug("Executing DETACH SQL for MySQL", zap.String("alias", mySQLDBAlias), zap.String("sql", detachSQLCmd))
		if _, err := m.helperDB.Exec(detachSQLCmd); err != nil {
			detachError = err // Capture detach error to return after table creation attempt
			m.logger.Error("Failed to detach MySQL database", zap.String("alias", mySQLDBAlias), zap.Error(detachError))
		} else {
			m.logger.Info("Successfully detached MySQL database", zap.String("alias", mySQLDBAlias))
		}
	}()

	// 2. CREATE TABLE ... AS ... statement for MotherDuck
	quotedTargetSchema := fmt.Sprintf("\"%s\"", m.dbName)
	quotedTargetTableName := fmt.Sprintf("\"%s\"", tableName)

	createTableSQL := fmt.Sprintf(`CREATE TABLE IF NOT EXISTS %s.%s AS %s`,
		quotedTargetSchema,
		quotedTargetTableName,
		sqlQuery,
	)

	m.logger.Debug("Executing CREATE TABLE AS SELECT SQL from MySQL",
		zap.String("target", fmt.Sprintf("%s.%s", m.dbName, tableName)),
		zap.String("sql", createTableSQL),
	)

	_, createErr := m.helperDB.Exec(createTableSQL)
	if createErr != nil {
		m.logger.Error("Failed to create table from MySQL data in MotherDuck",
			zap.String("target", fmt.Sprintf("%s.%s", m.dbName, tableName)),
			zap.Error(createErr),
		)
		return fmt.Errorf("creating table %s.%s from MySQL query (%s): %w", quotedTargetSchema, quotedTargetTableName, sqlQuery, createErr)
	}

	m.logger.Info("Successfully created table in MotherDuck from MySQL data",
		zap.String("target", fmt.Sprintf("%s.%s", m.dbName, tableName)),
	)

	if detachError != nil {
		m.logger.Warn("Table created successfully, but a non-critical error occurred during MySQL detach",
			zap.String("alias", mySQLDBAlias),
			zap.Error(detachError),
		)
	}

	return nil
}

// createTableFromMysqlDuckDB creates a table in local DuckDB by selecting data from an attached MySQL database.
func (m *OlapDBDriver) createTableFromMysqlDuckDB(connectionString, sqlQuery, tableName string) error {
	mySQLDBAlias := fmt.Sprintf("mysql_ext_%s", pkg.RandomString(10))
	parser, _ := sqlparser.New(sqlparser.Options{})
	parseResult, _ := parser.Parse(sqlQuery)
	node := parseResult.(*sqlparser.Select)
	WalkAndQualifyUnqualifiedTablesForMySQL(node, mySQLDBAlias)
	sqlQuery = sqlparser.String(node)

	// Parse the connection string into DuckDB MySQL format
	parsedConnectionString, err := parseMySQLConnectionString(connectionString)
	if err != nil {
		m.logger.Error("Failed to parse MySQL connection string", zap.Error(err))
		return fmt.Errorf("parsing MySQL connection string: %w", err)
	}

	// Mask password for logging
	logConnectionFormat := maskPasswordInConnectionString(parsedConnectionString)

	// 1. ATTACH statement for MySQL
	attachSQL := fmt.Sprintf(`ATTACH '%s' AS "%s" (TYPE MYSQL)`, parsedConnectionString, mySQLDBAlias)

	m.logger.Debug("Executing ATTACH SQL for MySQL",
		zap.String("alias", mySQLDBAlias),
		zap.String("connection_format", logConnectionFormat))
	if _, err := m.db.Exec(attachSQL); err != nil {
		m.logger.Error("Failed to attach MySQL database", zap.String("alias", mySQLDBAlias), zap.Error(err))
		return fmt.Errorf("attaching MySQL database (alias: %s): %w", mySQLDBAlias, err)
	}
	m.logger.Info("Successfully attached MySQL database", zap.String("alias", mySQLDBAlias))

	var detachError error
	defer func() {
		detachSQLCmd := fmt.Sprintf(`DETACH "%s"`, mySQLDBAlias)
		m.logger.Debug("Executing DETACH SQL for MySQL", zap.String("alias", mySQLDBAlias), zap.String("sql", detachSQLCmd))
		if _, err := m.db.Exec(detachSQLCmd); err != nil {
			detachError = err
			m.logger.Error("Failed to detach MySQL database", zap.String("alias", mySQLDBAlias), zap.Error(detachError))
		} else {
			m.logger.Info("Successfully detached MySQL database", zap.String("alias", mySQLDBAlias))
		}
	}()

	// 2. CREATE TABLE ... AS ... statement for local DuckDB
	quotedTargetTableName := fmt.Sprintf("\"%s\"", tableName)

	// sqlQuery needs to be a DuckDB query string that can select from the attached MySQL database
	createTableSQL := fmt.Sprintf(`CREATE TABLE IF NOT EXISTS %s AS %s`,
		quotedTargetTableName,
		sqlQuery,
	)

	m.logger.Debug("Executing CREATE TABLE AS SELECT SQL from MySQL",
		zap.String("target", tableName),
		zap.String("sql", createTableSQL),
	)

	_, createErr := m.db.Exec(createTableSQL)
	if createErr != nil {
		m.logger.Error("Failed to create table from MySQL data in DuckDB",
			zap.String("target", tableName),
			zap.Error(createErr),
		)
		return fmt.Errorf("creating table %s from MySQL query (%s): %w", quotedTargetTableName, sqlQuery, createErr)
	}

	m.logger.Info("Successfully created table in DuckDB from MySQL data",
		zap.String("target", tableName),
	)

	if detachError != nil {
		m.logger.Warn("Table created successfully, but a non-critical error occurred during MySQL detach",
			zap.String("alias", mySQLDBAlias),
			zap.Error(detachError),
		)
	}

	return nil
}

// maskPasswordInConnectionString replaces the password in a connection string with asterisks
func maskPasswordInConnectionString(connStr string) string {
	if strings.Contains(connStr, "password=") {
		re := regexp.MustCompile(`password=([^ ]*)`)
		return re.ReplaceAllString(connStr, "password=********")
	}
	return connStr
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

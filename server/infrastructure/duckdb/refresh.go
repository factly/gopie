package duckdb

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/infrastructure/duckdb/duckdbsql"
	"go.uber.org/zap"
)

// DatabaseType represents the source database type
type DatabaseType string

const (
	PostgresDB DatabaseType = "POSTGRES"
	MySQLDB    DatabaseType = "MYSQL"
)

// refreshConfig holds configuration for incremental refresh operations
// For incremental refresh, only new rows (based on timestampColumn) are inserted
type refreshConfig struct {
	db                   *sql.DB
	dbType               DatabaseType
	connectionString     string
	sqlQuery             string
	tableName            string
	timestampColumn      string
	lastRefreshTimestamp *time.Time
	isMotherDuck         bool
	motherDuckSchema     string
}

// fullRefreshConfig holds configuration for full refresh operations
type fullRefreshConfig struct {
	db               *sql.DB
	dbType           DatabaseType
	connectionString string
	sqlQuery         string
	tableName        string
	isMotherDuck     bool
	motherDuckSchema string
}

func (m *OlapDBDriver) IncrementalRefreshPostgres(connectionString, sqlQuery, tableName, timestampColumn string, lastRefreshTimestamp *time.Time) error {
	switch m.olapType {
	case "duckdb":
		return m.incrementalRefreshFromPostgresDuckDB(connectionString, sqlQuery, tableName, timestampColumn, lastRefreshTimestamp)
	case "motherduck":
		return m.increamentalRefreshFromPostgresMotherDuck(connectionString, sqlQuery, tableName, timestampColumn, lastRefreshTimestamp)
	default:
		return fmt.Errorf("unsupported olap type for incremental refresh: %s", m.olapType)
	}
}

func (m *OlapDBDriver) IncrementalRefreshMySQL(connectionString, sqlQuery, tableName, timestampColumn string, lastRefreshTimestamp *time.Time) error {
	switch m.olapType {
	case "duckdb":
		return m.increamentalReFreshFromMySQLDuckDB(connectionString, sqlQuery, tableName, timestampColumn, lastRefreshTimestamp)
	case "motherduck":
		return m.increamentalRefreshFromMySQLMotherDuck(connectionString, sqlQuery, tableName, timestampColumn, lastRefreshTimestamp)
	default:
		return fmt.Errorf("unsupported olap type for incremental refresh: %s", m.olapType)
	}
}

// incrementalRefreshFromPostgresDuckDB performs incremental refresh from PostgreSQL to DuckDB
func (m *OlapDBDriver) incrementalRefreshFromPostgresDuckDB(connectionString, sqlQuery, tableName, timestampColumn string, lastRefreshTimestamp *time.Time) error {
	return m.performIncrementalRefresh(refreshConfig{
		db:                   m.db,
		dbType:               PostgresDB,
		connectionString:     connectionString,
		sqlQuery:             sqlQuery,
		tableName:            tableName,
		timestampColumn:      timestampColumn,
		lastRefreshTimestamp: lastRefreshTimestamp,
		isMotherDuck:         false,
	})
}

// increamentalRefreshFromPostgresMotherDuck performs incremental refresh from PostgreSQL to MotherDuck
func (m *OlapDBDriver) increamentalRefreshFromPostgresMotherDuck(connectionString, sqlQuery, tableName, timestampColumn string, lastRefreshTimestamp *time.Time) error {
	return m.performIncrementalRefresh(refreshConfig{
		db:                   m.helperDB,
		dbType:               PostgresDB,
		connectionString:     connectionString,
		sqlQuery:             sqlQuery,
		tableName:            tableName,
		timestampColumn:      timestampColumn,
		lastRefreshTimestamp: lastRefreshTimestamp,
		isMotherDuck:         true,
		motherDuckSchema:     m.dbName,
	})
}

// increamentalReFreshFromMySQLDuckDB performs incremental refresh from MySQL to DuckDB
func (m *OlapDBDriver) increamentalReFreshFromMySQLDuckDB(connectionString, sqlQuery, tableName, timestampColumn string, lastRefreshTimestamp *time.Time) error {
	return m.performIncrementalRefresh(refreshConfig{
		db:                   m.db,
		dbType:               MySQLDB,
		connectionString:     connectionString,
		sqlQuery:             sqlQuery,
		tableName:            tableName,
		timestampColumn:      timestampColumn,
		lastRefreshTimestamp: lastRefreshTimestamp,
		isMotherDuck:         false,
	})
}

// increamentalRefreshFromMySQLMotherDuck performs incremental refresh from MySQL to MotherDuck
func (m *OlapDBDriver) increamentalRefreshFromMySQLMotherDuck(connectionString, sqlQuery, tableName, timestampColumn string, lastRefreshTimestamp *time.Time) error {
	return m.performIncrementalRefresh(refreshConfig{
		db:                   m.helperDB,
		dbType:               MySQLDB,
		connectionString:     connectionString,
		sqlQuery:             sqlQuery,
		tableName:            tableName,
		timestampColumn:      timestampColumn,
		lastRefreshTimestamp: lastRefreshTimestamp,
		isMotherDuck:         true,
		motherDuckSchema:     m.dbName,
	})
}

// performIncrementalRefresh is the unified implementation for all incremental refresh operations
func (m *OlapDBDriver) performIncrementalRefresh(cfg refreshConfig) (err error) {
	// Generate alias and determine target description
	dbAlias := m.generateDatabaseAlias(cfg.dbType)
	targetDesc := m.getTargetDescription(cfg.isMotherDuck)

	m.logger.Debug(
		fmt.Sprintf("starting incremental refresh%s", targetDesc),
		zap.String("table", cfg.tableName),
		zap.String("source", string(cfg.dbType)),
	)

	// Prepare connection string for MySQL if needed
	if cfg.dbType == MySQLDB {
		parsedConn, err := parseMySQLConnectionString(cfg.connectionString)
		if err != nil {
			m.logger.Error("Failed to parse MySQL connection string", zap.Error(err))
			return fmt.Errorf("parsing MySQL connection string: %w", err)
		}
		cfg.connectionString = parsedConn

		logConnectionFormat := maskPasswordInConnectionString(parsedConn)
		m.logger.Debug(
			fmt.Sprintf("Executing ATTACH SQL for MySQL%s", targetDesc),
			zap.String("alias", dbAlias),
			zap.String("connection_format", logConnectionFormat),
		)
	}

	// Attach source database
	if err := m.attachDatabase(cfg.db, cfg.connectionString, dbAlias, cfg.dbType, targetDesc); err != nil {
		return err
	}

	// Ensure detach on exit
	var detachError error
	defer func() {
		detachError = m.detachDatabase(cfg.db, dbAlias, targetDesc)
	}()

	// Perform the refresh within a transaction
	if err := m.executeRefreshTransaction(cfg, dbAlias, targetDesc); err != nil {
		return err
	}

	m.logger.Info(
		fmt.Sprintf("successfully completed incremental refresh%s", targetDesc),
		zap.String("table", cfg.tableName),
	)

	return detachError
}

// executeRefreshTransaction performs the insert operation for new rows within a transaction
func (m *OlapDBDriver) executeRefreshTransaction(cfg refreshConfig, dbAlias, targetDesc string) (err error) {
	tx, err := cfg.db.BeginTx(context.Background(), nil)
	if err != nil {
		m.logger.Error(fmt.Sprintf("failed to begin transaction for incremental refresh%s", targetDesc), zap.Error(err))
		return err
	}

	defer func() {
		if p := recover(); p != nil {
			tx.Rollback()
			panic(p)
		} else if err != nil {
			m.logger.Warn(fmt.Sprintf("rolling back transaction due to error%s", targetDesc), zap.Error(err))
			tx.Rollback()
		}
	}()

	// Insert only new rows
	if err = m.executeInsertNewRows(tx, cfg, dbAlias, targetDesc); err != nil {
		return err
	}

	if err = tx.Commit(); err != nil {
		m.logger.Error(fmt.Sprintf("failed to commit incremental refresh transaction%s", targetDesc), zap.Error(err))
		return fmt.Errorf("committing transaction: %w", err)
	}

	return nil
}

// executeInsertNewRows inserts only new rows based on timestamp filter
func (m *OlapDBDriver) executeInsertNewRows(tx *sql.Tx, cfg refreshConfig, dbAlias, targetDesc string) error {
	m.logger.Debug(fmt.Sprintf("preparing insert query for new rows%s", targetDesc))

	insertAst, err := duckdbsql.Parse(cfg.db, cfg.sqlQuery)
	if err != nil {
		return fmt.Errorf("parsing SQL query for insert: %w", err)
	}

	if err = insertAst.QualifyUnqualifiedTables(dbAlias); err != nil {
		return fmt.Errorf("qualifying tables for insert: %w", err)
	}

	// Add timestamp filter to get only new rows
	timestampFilter := fmt.Sprintf(`"%s" > '%s'`, cfg.timestampColumn, cfg.lastRefreshTimestamp.Format(time.RFC3339Nano))
	if err = insertAst.AddWhere(timestampFilter); err != nil {
		return fmt.Errorf("adding timestamp filter to query: %w", err)
	}

	insertSelectSQL, err := insertAst.Format()
	if err != nil {
		return fmt.Errorf("formatting insert query: %w", err)
	}

	targetTable := m.getQualifiedTableName(cfg.tableName, cfg.isMotherDuck, cfg.motherDuckSchema)
	insertSQL := fmt.Sprintf(
		`INSERT INTO %s SELECT * FROM (%s)`,
		targetTable, insertSelectSQL,
	)

	m.logger.Debug(fmt.Sprintf("executing insert query for new rows%s", targetDesc), zap.String("query", insertSQL))
	result, err := tx.Exec(insertSQL)
	if err != nil {
		return fmt.Errorf("executing insert for new rows: %w", err)
	}

	rowsInserted, _ := result.RowsAffected()
	m.logger.Info(fmt.Sprintf("insert step completed%s", targetDesc), zap.Int64("rows_inserted", rowsInserted))
	return nil
}

func (m *OlapDBDriver) FullTableRefreshPostgres(connectionString, sqlQuery, tableName string) error {
	switch m.olapType {
	case "duckdb":
		return m.fullTableRefreshFromPostgresDuckDB(connectionString, sqlQuery, tableName)
	case "motherduck":
		return m.fullTableRefreshFromPostgresMotherDuck(connectionString, sqlQuery, tableName)
	default:
		return fmt.Errorf("unsupported olap type for full table refresh: %s", m.olapType)
	}
}

func (m *OlapDBDriver) FullTableRefreshMySQL(connectionString, sqlQuery, tableName string) error {
	switch m.olapType {
	case "duckdb":
		return m.fullTableRefreshFromMySQLDuckDB(connectionString, sqlQuery, tableName)
	case "motherduck":
		return m.fullTableRefreshFromMySQLMotherDuck(connectionString, sqlQuery, tableName)
	default:
		return fmt.Errorf("unsupported olap type for full table refresh: %s", m.olapType)
	}
}

// fullTableRefreshFromPostgresDuckDB performs full refresh from PostgreSQL to DuckDB
func (m *OlapDBDriver) fullTableRefreshFromPostgresDuckDB(connectionString, sqlQuery, tableName string) error {
	return m.performFullRefresh(fullRefreshConfig{
		db:               m.db,
		dbType:           PostgresDB,
		connectionString: connectionString,
		sqlQuery:         sqlQuery,
		tableName:        tableName,
		isMotherDuck:     false,
	})
}

// fullTableRefreshFromPostgresMotherDuck performs full refresh from PostgreSQL to MotherDuck
func (m *OlapDBDriver) fullTableRefreshFromPostgresMotherDuck(connectionString, sqlQuery, tableName string) error {
	return m.performFullRefresh(fullRefreshConfig{
		db:               m.helperDB,
		dbType:           PostgresDB,
		connectionString: connectionString,
		sqlQuery:         sqlQuery,
		tableName:        tableName,
		isMotherDuck:     true,
		motherDuckSchema: m.dbName,
	})
}

// fullTableRefreshFromMySQLDuckDB performs full refresh from MySQL to DuckDB
func (m *OlapDBDriver) fullTableRefreshFromMySQLDuckDB(connectionString, sqlQuery, tableName string) error {
	return m.performFullRefresh(fullRefreshConfig{
		db:               m.db,
		dbType:           MySQLDB,
		connectionString: connectionString,
		sqlQuery:         sqlQuery,
		tableName:        tableName,
		isMotherDuck:     false,
	})
}

// fullTableRefreshFromMySQLMotherDuck performs full refresh from MySQL to MotherDuck
func (m *OlapDBDriver) fullTableRefreshFromMySQLMotherDuck(connectionString, sqlQuery, tableName string) error {
	return m.performFullRefresh(fullRefreshConfig{
		db:               m.helperDB,
		dbType:           MySQLDB,
		connectionString: connectionString,
		sqlQuery:         sqlQuery,
		tableName:        tableName,
		isMotherDuck:     true,
		motherDuckSchema: m.dbName,
	})
}

// performFullRefresh is the unified implementation for all full refresh operations
func (m *OlapDBDriver) performFullRefresh(cfg fullRefreshConfig) (err error) {
	// Generate alias and determine target description
	dbAlias := m.generateDatabaseAlias(cfg.dbType)
	targetDesc := m.getTargetDescription(cfg.isMotherDuck)

	m.logger.Debug(
		fmt.Sprintf("starting full table refresh%s", targetDesc),
		zap.String("table", cfg.tableName),
		zap.String("source", string(cfg.dbType)),
	)

	// Prepare connection string for MySQL if needed
	if cfg.dbType == MySQLDB {
		parsedConn, err := parseMySQLConnectionString(cfg.connectionString)
		if err != nil {
			m.logger.Error("Failed to parse MySQL connection string", zap.Error(err))
			return fmt.Errorf("parsing MySQL connection string: %w", err)
		}
		cfg.connectionString = parsedConn
	}

	// Attach source database
	if err := m.attachDatabase(cfg.db, cfg.connectionString, dbAlias, cfg.dbType, targetDesc); err != nil {
		return err
	}

	// Ensure detach on exit
	var detachError error
	defer func() {
		detachError = m.detachDatabase(cfg.db, dbAlias, targetDesc)
	}()

	// Perform the full refresh within a transaction
	if err := m.executeFullRefreshTransaction(cfg, targetDesc, dbAlias); err != nil {
		return err
	}

	m.logger.Info("Successfully created table",
		zap.String("target", fmt.Sprintf("%s.%s", m.dbName, cfg.tableName)),
	)

	if detachError != nil {
		m.logger.Warn(fmt.Sprintf("Table created successfully, but a non-critical error occurred during %s detach", cfg.dbType),
			zap.String("alias", dbAlias),
			zap.Error(detachError),
		)
	}

	return nil
}

// executeFullRefreshTransaction performs the drop and create operations within a transaction
func (m *OlapDBDriver) executeFullRefreshTransaction(cfg fullRefreshConfig, targetDesc, dbAlias string) (err error) {
	// qualify the select query
	qualifiedSelectAst, err := duckdbsql.Parse(cfg.db, cfg.sqlQuery)
	if err != nil {
		m.logger.Error(fmt.Sprintf("failed to parse SQL query for full refresh%s", targetDesc), zap.Error(err))
		return fmt.Errorf("parsing SQL query for full refresh: %w", err)
	}
	if err = qualifiedSelectAst.QualifyUnqualifiedTables(dbAlias); err != nil {
		m.logger.Error(fmt.Sprintf("failed to qualify tables in SQL query for full refresh%s", targetDesc), zap.Error(err))
		return fmt.Errorf("qualifying tables in SQL query for full refresh: %w", err)
	}

	cfg.sqlQuery, err = qualifiedSelectAst.Format()
	if err != nil {
		m.logger.Error(fmt.Sprintf("failed to format qualified SQL query for full refresh%s", targetDesc), zap.Error(err))
		return fmt.Errorf("formatting qualified SQL query for full refresh: %w", err)
	}
	m.logger.Debug(fmt.Sprintf("qualified SQL query for full refresh%s", targetDesc), zap.String("query", cfg.sqlQuery))

	tx, err := cfg.db.BeginTx(context.Background(), nil)
	if err != nil {
		m.logger.Error(fmt.Sprintf("failed to begin transaction for full table refresh%s", targetDesc), zap.Error(err))
		return err
	}

	defer func() {
		if p := recover(); p != nil {
			tx.Rollback()
			panic(p)
		} else if err != nil {
			m.logger.Warn(fmt.Sprintf("rolling back transaction due to error%s", targetDesc), zap.Error(err))
			tx.Rollback()
		}
	}()

	// Drop existing table
	if err = m.dropTableIfExists(tx, cfg.tableName, targetDesc); err != nil {
		return err
	}

	// Create table from the qualified select
	if err = m.createTableFromSelect(tx, m.dbName, cfg.tableName, cfg.sqlQuery); err != nil {
		return err
	}

	if err = tx.Commit(); err != nil {
		m.logger.Error(fmt.Sprintf("failed to commit full table refresh transaction%s", targetDesc), zap.Error(err))
		return fmt.Errorf("committing transaction: %w", err)
	}

	return nil
}

// attachDatabase attaches the source database
func (m *OlapDBDriver) attachDatabase(db *sql.DB, connectionString, alias string, dbType DatabaseType, targetDesc string) error {
	attachSQL := fmt.Sprintf(`ATTACH '%s' AS "%s" (TYPE %s)`, connectionString, alias, dbType)

	if _, err := db.Exec(attachSQL); err != nil {
		m.logger.Error(
			fmt.Sprintf("Failed to attach %s database%s", dbType, targetDesc),
			zap.String("alias", alias),
			zap.Error(err),
		)
		return fmt.Errorf("attaching %s database (alias: %s): %w", dbType, alias, err)
	}

	m.logger.Info(fmt.Sprintf("Successfully attached %s database%s", dbType, targetDesc), zap.String("alias", alias))
	return nil
}

// detachDatabase detaches the source database
func (m *OlapDBDriver) detachDatabase(db *sql.DB, alias, targetDesc string) error {
	detachSQL := fmt.Sprintf(`DETACH "%s"`, alias)
	m.logger.Debug(fmt.Sprintf("Executing DETACH SQL%s", targetDesc), zap.String("alias", alias), zap.String("sql", detachSQL))

	if _, err := db.Exec(detachSQL); err != nil {
		m.logger.Error(fmt.Sprintf("Failed to detach database%s", targetDesc), zap.String("alias", alias), zap.Error(err))
		return err
	}

	m.logger.Info(fmt.Sprintf("Successfully detached database%s", targetDesc), zap.String("alias", alias))
	return nil
}

// generateDatabaseAlias creates a unique alias for the attached database
func (m *OlapDBDriver) generateDatabaseAlias(dbType DatabaseType) string {
	prefix := "pg_ext"
	if dbType == MySQLDB {
		prefix = "mysql_ext"
	}
	return fmt.Sprintf("%s_%s", prefix, pkg.RandomString(10))
}

// getQualifiedTableName returns the properly qualified table name
func (m *OlapDBDriver) getQualifiedTableName(tableName string, isMotherDuck bool, schema string) string {
	if isMotherDuck {
		return fmt.Sprintf(`"%s"."%s"`, schema, tableName)
	}
	return fmt.Sprintf(`"%s"`, tableName)
}

// getTargetDescription returns a description string for logging
func (m *OlapDBDriver) getTargetDescription(isMotherDuck bool) string {
	if isMotherDuck {
		return " (MotherDuck)"
	}
	return ""
}

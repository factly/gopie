package duckdb

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"time"

	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/duckdb/duckdbsql"
	"github.com/huandu/go-sqlbuilder"
	"go.uber.org/zap"
)

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
func (m *OlapDBDriver) createTableInternal(tx *sql.Tx, sourcePath, tableName, format string, alterColumnNames map[string]string, isS3 bool, ignoreErrors bool) (err error) {
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

	if ignoreErrors && format == "csv" {
		lastParen := strings.LastIndex(readFunc, ")")
		if lastParen != -1 {
			// Injects ignore_errors=true into the read function call.
			// e.g., "read_csv_auto('path')" becomes "read_csv_auto('path', ignore_errors=true)"
			readFunc = readFunc[:lastParen] + ", ignore_errors=true)"
			m.logger.Debug("added ignore_errors=true to read function for DuckDB")
		}
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

	// if transaction is not passed
	// start a new transaction
	var startedTx bool
	if tx == nil {
		tx, err = m.db.BeginTx(context.Background(), nil)
		if err != nil {
			m.logger.Error(fmt.Sprintf("error starting transaction for CreateTableFrom%s", dataSourceType), zap.Error(err))
			return err
		}
		startedTx = true
	}

	m.logger.Info("generated sql", zap.String("createSql", createSql))

	_, err = tx.Exec(createSql)
	if err != nil {
		if startedTx {
			tx.Rollback()
		}
		m.logger.Error(fmt.Sprintf("error executing create table from %s query", dataSourceType), zap.String("query", createSql), zap.Error(err))
		return parseError(fmt.Errorf("failed creating table '%s' from %s: %w", tableName, dataSourceType, err))
	}
	m.logger.Info(fmt.Sprintf("successfully created/replaced table from %s", dataSourceType), zap.String("tableName", tableName), zap.String("sourcePath", sourcePath))

	if err = m.renameTableColumns(tx, tableName, alterColumnNames, m.logger); err != nil {
		if startedTx {
			tx.Rollback()
		}
		m.logger.Error(fmt.Sprintf("error renaming columns in table created from %s", dataSourceType), zap.String("tableName", tableName), zap.Error(err))
		return err
	}

	if startedTx {
		if err = tx.Commit(); err != nil {
			m.logger.Error(fmt.Sprintf("error committing transaction for CreateTableFrom%s", dataSourceType), zap.Error(err))
			return fmt.Errorf("failed to commit transaction for CreateTableFrom%s: %w", dataSourceType, err)
		}
	}

	return nil
}

// CreateTable creates a table in DuckDB by reading data from a local file path.
func (m *OlapDBDriver) CreateTable(filePath, tableName, format string, alterColumnNames map[string]string, ignoreErrors bool) error {
	return m.createTableInternal(nil, filePath, tableName, format, alterColumnNames, false, ignoreErrors)
}

// CreateTableFromS3 creates a table in DuckDB by reading data from an S3 path.
func (m *OlapDBDriver) CreateTableFromS3(s3Path, tableName, format string, alterColumnNames map[string]string, ignoreErrors bool) error {
	return m.createTableInternal(nil, s3Path, tableName, format, alterColumnNames, true, ignoreErrors)
}

func (m *OlapDBDriver) CreateTableFromS3WithTx(tx *sql.Tx, s3Path, tableName, format string, alterColumnNames map[string]string, ignoreErrors bool) error {
	return m.createTableInternal(tx, s3Path, tableName, format, alterColumnNames, true, ignoreErrors)
}

func (m *OlapDBDriver) DropTableWithTx(tx *sql.Tx, tableName string) error {
	escapedTableName := sqlbuilder.Escape(tableName)
	sqlCmd := fmt.Sprintf("DROP TABLE IF EXISTS %s", escapedTableName)
	m.logger.Debug("executing drop table query within transaction", zap.String("query", sqlCmd))
	_, err := tx.Exec(sqlCmd)
	if err != nil {
		m.logger.Error("error dropping table within transaction", zap.String("tableName", tableName), zap.Error(err))
		return parseError(fmt.Errorf("failed dropping table '%s' within transaction: %w", tableName, err))
	}
	m.logger.Info("successfully dropped table within transaction", zap.String("tableName", tableName))
	return nil
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

// CreateTableFromMySql creates a table in DuckDB by executing a query on a MySQL database
func (m *OlapDBDriver) CreateTableFromMySql(connectionString, sqlQuery, tableName string) error {
	if m.olapType == "motherduck" {
		return m.createTableFromMysqlMotherDuck(connectionString, sqlQuery, tableName)
	} else {
		return m.createTableFromMysqlDuckDB(connectionString, sqlQuery, tableName)
	}
}

func (m *OlapDBDriver) createTableFromPostgresMotherDuck(connectionString, sqlQuery, tableName string) error {
	pgDBAlias := fmt.Sprintf("pg_ext_%s", pkg.RandomString(10))
	m.logger.Debug("parsed SQL query", zap.String("query", sqlQuery))

	ast, err := duckdbsql.Parse(m.helperDB, sqlQuery)
	if err != nil {
		m.logger.Error("failed to parse SQL query", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("parsing SQL query: %w", err)
	}

	err = ast.QualifyUnqualifiedTables(pgDBAlias)
	if err != nil {
		m.logger.Error("failed to qualify unqualified table names in SQL query", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("qualifying unqualified table names in SQL query: %w", err)
	}

	sqlQuery, err = ast.Format()
	if err != nil {
		m.logger.Error("failed to format SQL query after qualifying table names", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("formatting SQL query after qualifying table names: %w", err)
	}

	m.logger.Debug("deparsed SQL query", zap.String("query", sqlQuery))

	attachSQL := fmt.Sprintf(`ATTACH '%s' AS "%s" (TYPE POSTGRES)`, connectionString, pgDBAlias) // Quoting alias just in case, though generated ones are usually safe.

	m.logger.Debug("Executing ATTACH SQL", zap.String("alias", pgDBAlias))
	if _, err := m.helperDB.Exec(attachSQL); err != nil {
		m.logger.Error("Failed to attach PostgreSQL database", zap.String("alias", pgDBAlias), zap.Error(err))
		return fmt.Errorf("attaching PostgreSQL database (alias: %s): %w", pgDBAlias, err)
	}
	m.logger.Info("Successfully attached PostgreSQL database", zap.String("alias", pgDBAlias))

	var detachError error
	defer func() {
		detachSQLCmd := fmt.Sprintf(`DETACH "%s"`, pgDBAlias) // Quoted alias
		m.logger.Debug("Executing DETACH SQL", zap.String("alias", pgDBAlias), zap.String("sql", detachSQLCmd))
		if _, err := m.helperDB.Exec(detachSQLCmd); err != nil {
			detachError = err
			m.logger.Error("Failed to detach PostgreSQL database", zap.String("alias", pgDBAlias), zap.Error(detachError))
		} else {
			m.logger.Info("Successfully detached PostgreSQL database", zap.String("alias", pgDBAlias))
		}
	}()

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
	m.logger.Debug("parsed SQL query", zap.String("query", sqlQuery))

	ast, err := duckdbsql.Parse(m.db, sqlQuery)
	if err != nil {
		m.logger.Error("failed to parse SQL query", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("parsing SQL query: %w", err)
	}

	err = ast.QualifyUnqualifiedTables(pgDBAlias)
	if err != nil {
		m.logger.Error("failed to qualify unqualified table names in SQL query", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("qualifying unqualified table names in SQL query: %w", err)
	}

	sqlQuery, err = ast.Format()
	if err != nil {
		m.logger.Error("failed to format SQL query after qualifying table names", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("formatting SQL query after qualifying table names: %w", err)
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
	mySQLDBAlias := fmt.Sprintf("mysql_ext_%s", pkg.RandomString(10))

	ast, err := duckdbsql.Parse(m.helperDB, sqlQuery)
	if err != nil {
		m.logger.Error("failed to parse SQL query", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("parsing SQL query: %w", err)
	}

	err = ast.QualifyUnqualifiedTables(mySQLDBAlias)
	if err != nil {
		m.logger.Error("failed to qualify unqualified table names in SQL query", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("qualifying unqualified table names in SQL query: %w", err)
	}

	sqlQuery, err = ast.Format()
	if err != nil {
		m.logger.Error("failed to format SQL query after qualifying table names", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("formatting SQL query after qualifying table names: %w", err)
	}

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
	mySqlDBAlias := fmt.Sprintf("mysql_ext_%s", pkg.RandomString(10))

	ast, err := duckdbsql.Parse(m.db, sqlQuery)
	if err != nil {
		m.logger.Error("failed to parse SQL query", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("parsing SQL query: %w", err)
	}

	err = ast.QualifyUnqualifiedTables(mySqlDBAlias)
	if err != nil {
		m.logger.Error("failed to qualify unqualified table names in SQL query", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("qualifying unqualified table names in SQL query: %w", err)
	}

	sqlQuery, err = ast.Format()
	if err != nil {
		m.logger.Error("failed to format SQL query after qualifying table names", zap.String("query", sqlQuery), zap.Error(err))
		return fmt.Errorf("formatting SQL query after qualifying table names: %w", err)
	}
	m.logger.Debug("deparsed SQL query", zap.String("query", sqlQuery))

	// Parse the connection string into DuckDB MySQL format
	parsedConnectionString, err := parseMySQLConnectionString(connectionString)
	if err != nil {
		m.logger.Error("Failed to parse MySQL connection string", zap.Error(err))
		return fmt.Errorf("parsing MySQL connection string: %w", err)
	}

	// Mask password for logging
	logConnectionFormat := maskPasswordInConnectionString(parsedConnectionString)

	// 1. ATTACH statement for MySQL
	attachSQL := fmt.Sprintf(`ATTACH '%s' AS "%s" (TYPE MYSQL)`, parsedConnectionString, mySqlDBAlias)

	m.logger.Debug("Executing ATTACH SQL for MySQL",
		zap.String("alias", mySqlDBAlias),
		zap.String("connection_format", logConnectionFormat))
	if _, err := m.db.Exec(attachSQL); err != nil {
		m.logger.Error("Failed to attach MySQL database", zap.String("alias", mySqlDBAlias), zap.Error(err))
		return fmt.Errorf("attaching MySQL database (alias: %s): %w", mySqlDBAlias, err)
	}
	m.logger.Info("Successfully attached MySQL database", zap.String("alias", mySqlDBAlias))

	var detachError error
	defer func() {
		detachSQLCmd := fmt.Sprintf(`DETACH "%s"`, mySqlDBAlias)
		m.logger.Debug("Executing DETACH SQL for MySQL", zap.String("alias", mySqlDBAlias), zap.String("sql", detachSQLCmd))
		if _, err := m.db.Exec(detachSQLCmd); err != nil {
			detachError = err
			m.logger.Error("Failed to detach MySQL database", zap.String("alias", mySqlDBAlias), zap.Error(detachError))
		} else {
			m.logger.Info("Successfully detached MySQL database", zap.String("alias", mySqlDBAlias))
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
			zap.String("alias", mySqlDBAlias),
			zap.Error(detachError),
		)
	}

	return nil
}

// parseAndQualifySQL parses the given raw SQL, qualifies unqualified tables with the provided alias, and returns the formatted SQL string.
func (m *OlapDBDriver) parseAndQualifySQL(db *sql.DB, rawSQL, alias string) (string, error) {
	ast, err := duckdbsql.Parse(db, rawSQL)
	if err != nil {
		m.logger.Error("failed to parse SQL query", zap.String("query", rawSQL), zap.Error(err))
		return "", fmt.Errorf("parsing SQL query: %w", err)
	}

	err = ast.QualifyUnqualifiedTables(alias)
	if err != nil {
		m.logger.Error("failed to qualify unqualified table names in SQL query", zap.String("query", rawSQL), zap.Error(err))
		return "", fmt.Errorf("qualifying unqualified table names in SQL query: %w", err)
	}

	qualifiedSQL, err := ast.Format()
	if err != nil {
		m.logger.Error("failed to format SQL query after qualifying table names", zap.String("query", rawSQL), zap.Error(err))
		return "", fmt.Errorf("formatting SQL query after qualifying table names: %w", err)
	}

	m.logger.Debug("qualified SQL query", zap.String("query", qualifiedSQL))
	return qualifiedSQL, nil
}

// dropTableIfExists drops the specified table within a transaction, logging the operation.
func (m *OlapDBDriver) dropTableIfExists(tx *sql.Tx, tableName, targetDesc string) error {
	var dropSQL string

	if m.olapType == "motherduck" {
		// For MotherDuck, qualify with schema
		dropSQL = fmt.Sprintf(`DROP TABLE IF EXISTS "%s"."%s"`, m.dbName, tableName)
	} else {
		// For local DuckDB
		dropSQL = fmt.Sprintf(`DROP TABLE IF EXISTS "%s"`, tableName)
	}

	m.logger.Debug(fmt.Sprintf("dropping existing table if exists%s", targetDesc), zap.String("query", dropSQL))

	_, err := tx.Exec(dropSQL)
	if err != nil {
		m.logger.Error(fmt.Sprintf("failed to drop table%s", targetDesc), zap.Error(err))
		return fmt.Errorf("dropping table: %w", err)
	}

	m.logger.Info("successfully dropped table within transaction", zap.String("tableName", tableName))
	return nil
}

// createTableFromSelect creates a table in the target schema from the given select SQL within a transaction.
func (m *OlapDBDriver) createTableFromSelect(tx *sql.Tx, schema, tableName, selectSQL string) error {
	quotedTargetSchema := fmt.Sprintf("\"%s\"", schema)
	quotedTargetTableName := fmt.Sprintf("\"%s\"", tableName)
	var createTableSQL string
	if m.olapType == "motherduck" {
		createTableSQL = fmt.Sprintf(`CREATE TABLE IF NOT EXISTS %s.%s AS %s`,
			quotedTargetSchema,
			quotedTargetTableName,
			selectSQL,
		)
	} else {
		createTableSQL = fmt.Sprintf(`CREATE TABLE IF NOT EXISTS %s AS %s`,
			quotedTargetTableName,
			selectSQL,
		)
	}
	m.logger.Debug("Executing CREATE TABLE AS SELECT SQL",
		zap.String("target", fmt.Sprintf("%s.%s", schema, tableName)),
		zap.String("sql", createTableSQL),
	)
	_, createErr := tx.Exec(createTableSQL)
	if createErr != nil {
		m.logger.Error("Failed to create table from source data",
			zap.String("target", fmt.Sprintf("%s.%s", schema, tableName)),
			zap.Error(createErr),
		)
		return fmt.Errorf("creating table %s.%s using SQL query (%s): %w", quotedTargetSchema, quotedTargetTableName, selectSQL, createErr)
	}
	m.logger.Info("Successfully created table",
		zap.String("target", fmt.Sprintf("%s.%s", schema, tableName)),
	)
	return nil
}

func (m *OlapDBDriver) GetLatestTimestamp(tableName, timestampColumn string) (*string, error) {
	escapedTableName := sqlbuilder.Escape(tableName)
	escapedTimestampCol := sqlbuilder.Escape(timestampColumn)

	query := fmt.Sprintf("SELECT MAX(%s) AS latest_timestamp FROM %s", escapedTimestampCol, escapedTableName)
	m.logger.Debug("executing latest timestamp query", zap.String("query", query))
	row := m.db.QueryRow(query)

	var latestTimestamp sql.NullTime
	if err := row.Scan(&latestTimestamp); err != nil {
		m.logger.Error("error scanning latest timestamp", zap.String("tableName", tableName), zap.String("timestampColumn", timestampColumn), zap.Error(err))
		return nil, parseError(fmt.Errorf("failed retrieving latest timestamp from table '%s': %w", tableName, err))
	}

	if latestTimestamp.Valid {
		tsString := latestTimestamp.Time.Format(time.RFC3339Nano)
		m.logger.Info("successfully retrieved latest timestamp", zap.String("tableName", tableName), zap.String("timestampColumn", timestampColumn), zap.String("latestTimestamp", tsString))
		return &tsString, nil
	}

	m.logger.Info("no valid timestamps found in table", zap.String("tableName", tableName), zap.String("timestampColumn", timestampColumn))
	return nil, nil
}

package duckdb

import (
	"context"
	"database/sql/driver"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/XSAM/otelsql"
	"github.com/factly/gopie/custom_errors"
	"github.com/factly/gopie/pkg"
	"github.com/jmoiron/sqlx"
	"github.com/marcboeker/go-duckdb"
)

type Connection struct {
	db     *sqlx.DB
	config *Config
	logger *pkg.Logger
	ctx    context.Context
}

func (c *Connection) Close() error {
	return c.db.Close()
}

func (c *Connection) reopenDB() error {
	if c.db != nil {
		err := c.db.Close()
		if err != nil {
			return err
		}
		c.db = nil
	}

	var bootQueries []string

	if c.config.BootQueries != "" {
		bootQueries = append(bootQueries, c.config.BootQueries)
	}

	bootQueries = append(bootQueries,
		"INSTALL 'json'",
		"LOAD 'json'",
		"INSTALL 'icu'",
		"LOAD 'icu'",
		"INSTALL 'parquet'",
		"LOAD 'parquet'",
		"INSTALL 'httpfs'",
		"LOAD 'httpfs'",
		"INSTALL 'sqlite'",
		"LOAD 'sqlite'",
		"SET max_expression_depth TO 250",
		"SET timezone='UTC'",
		"SET old_implicit_casting = true", // Implicit Cast to VARCHAR
	)

	if !c.config.AllowHostAccess {
		bootQueries = append(bootQueries, "SET preserve_insertion_order TO false")
	}

	// make the connection to be read-only
	// dsn := fmt.Sprintf("%saccess_mode=read_only", c.config.DSN)
	// TODO: make the dsn read_only if mentioned in the envs
	dsn := c.config.DSN

	connector, err := duckdb.NewConnector(dsn, func(execer driver.ExecerContext) error {
		for _, qry := range bootQueries {
			_, err := execer.ExecContext(context.Background(), qry, nil)
			if err != nil && strings.Contains(err.Error(), "Failed to download extension") {
				_, err = execer.ExecContext(context.Background(), qry+"FROM 'http://nightly-extensions.duckdb.org'", nil)
			}

			if err != nil {
				return err
			}
		}
		return nil
	})

	if err != nil {
		if strings.Contains(err.Error(), "Trying to read a database file with version number") {
			return fmt.Errorf("database file %q was created with an older, incompatible verison of Gopie (please remove it and try again)", c.config.DSN)
		}

		if strings.Contains(err.Error(), "Could not set lock on file") {
			return fmt.Errorf("failed to open database (is gopie already running?): %w", err)
		}

		return err
	}

	sqlDB := otelsql.OpenDB(connector)
	db := sqlx.NewDb(sqlDB, "duckdb")
	db.SetMaxOpenConns(c.config.PoolSize)
	c.db = db

	if !c.config.ExtTableStorage {
		return nil
	}

	conn, err := db.Connx(context.Background())

	if err != nil {
		return nil
	}

	defer conn.Close()

	_, err = conn.ExecContext(context.Background(), `
		select
			coalesce(t.table_catalog, current_database()) as "database",
			t.table_schema as "schema",
			t.table_name as "name",
			t.table_type as "type", 
			array_agg(c.column_name order by c.ordinal_position) as "column_names",
			array_agg(c.data_type order by c.ordinal_position) as "column_types",
			array_agg(c.is_nullable = 'YES' order by c.ordinal_position) as "column_nullable"
		from information_schema.tables t
		join information_schema.columns c on t.table_schema = c.table_schema and t.table_name = c.table_name
		group by 1, 2, 3, 4
		order by 1, 2, 3, 4
	`)
	if err != nil {
		return err
	}

	entries, err := os.ReadDir(c.config.DBStoragePath)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		path := filepath.Join(c.config.DBStoragePath, entry.Name())
		version, exist, err := c.tableVersion(entry.Name())

		if err != nil {
			c.logger.Error("error in fetching db verison: ", err.Error())
			_ = os.RemoveAll(path)
			continue
		}
		if !exist {
			_ = os.RemoveAll(path)
			continue
		}

		dbFile := filepath.Join(path, fmt.Sprintf("%s.db", version))
		db := dbName(entry.Name(), version)
		_, err = conn.ExecContext(context.Background(), fmt.Sprintf("ATTACH %s AS %s", safeSQLString(dbFile), safeSQLName(db)))

		if err != nil {
			c.logger.Error("attach failed clearing db file", err.Error())
			_, _ = conn.ExecContext(context.Background(), fmt.Sprintf("DROP VIEW IF EXISTS %s", safeSQLName(entry.Name())))
			_ = os.RemoveAll(path)
		}
	}

	return nil
}

func (c *Connection) tableVersion(name string) (string, bool, error) {
	pathToFile := filepath.Join(c.config.DBStoragePath, name, "version.txt")
	contents, err := os.ReadFile(pathToFile)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			return "", false, nil
		}
		return "", false, err
	}
	return strings.TrimSpace(string(contents)), true, nil
}

// TODO: change this type of usage
var conn *sqlx.Conn

func (c *Connection) Execute(ctx context.Context, stmt *Statement) (res *Result, outErr error) {
	c.logger.Info(fmt.Sprintf("running duckdb query: %v, %v", stmt.Query, stmt.Args))

	if conn == nil {
		var err error
		conn, err = c.db.Connx(ctx)
		if err != nil {
			return nil, fmt.Errorf("error create a connection: %s", err.Error())
		}
	}

	rows, err := conn.QueryContext(ctx, stmt.Query, stmt.Args...)
	if err != nil {
		// TODO: find a better to handle this error
		if strings.Contains(err.Error(), "does not exist!") {
			return nil, custom_errors.TableNotFound
		}
		return nil, err
	}

	schema, err := RowsToSchema(rows)
	if err != nil {
		return nil, err
	}
	res = &Result{
		Schema: schema,
		Rows:   rows,
	}

	return res, nil
}

func (c *Connection) CreateTableAsSelect(ctx context.Context, name string, sql string) error {
	c.logger.Info(fmt.Sprintf("create table %s", name))

	if !c.config.ExtTableStorage {
		return fmt.Errorf("gopie only supports exteranl table storages")
	}

	sourceDir := filepath.Join(c.config.DBStoragePath, name)
	if err := os.Mkdir(sourceDir, fs.ModePerm); err != nil && !errors.Is(err, fs.ErrExist) {
		return fmt.Errorf("create: unable to create dir %q: %w", sourceDir, err)
	}

	oldVerison, oldVersionExists, _ := c.tableVersion(name)
	newVersion := fmt.Sprint(time.Now().UnixMilli())
	dbFile := filepath.Join(sourceDir, fmt.Sprintf("%s.db", newVersion))
	db := dbName(name, newVersion)

	_, err := c.Execute(ctx, &Statement{
		Query: fmt.Sprintf("ATTACH %s AS %s", fmt.Sprintf("'%s'", dbFile), safeName(db)),
	})
	if err != nil {
		// removeDBFile(dbFile)
		return fmt.Errorf("create: attatch %q db failed: %w", dbFile, err)
	}

	_, err = c.Execute(ctx, &Statement{
		Query: fmt.Sprintf("CREATE OR REPLACE TABLE %s.default AS (%s\n)", safeSQLName(db), sql),
	})

	if err != nil {
		c.logger.Error(err.Error())
		return err
	}

	err = c.updateVersion(name, newVersion)
	if err != nil {
		c.detachAndRemoveFile(db, dbFile)
		return err
	}

	qry, err := c.generateSelectQuery(ctx, db)
	if err != nil {
		return err
	}

	_, err = c.Execute(ctx, &Statement{
		Query: fmt.Sprintf("CREATE OR REPLACE VIEW %s AS %s", safeSQLName(name), qry),
	})
	if err != nil {
		c.logger.Error(err.Error())
		return fmt.Errorf("CREATE OR REPLACE VIEW %s AS %s", safeSQLName(name), qry)
	}
	if oldVersionExists {
		oldDB := dbName(name, oldVerison)
		c.detachAndRemoveFile(oldDB, filepath.Join(sourceDir, fmt.Sprintf("%s.db", oldVerison)))
	}

	return nil
}

func (c *Connection) InsertTableAsSelect(ctx context.Context, name string, byName bool, sql string) error {
	c.logger.Info(fmt.Sprintf("insert into table %s", name))
	var insertByNameClause string
	if byName {
		insertByNameClause = "BY NAME"
	} else {
		insertByNameClause = ""
	}

	if !c.config.ExtTableStorage {
		return fmt.Errorf("gopie only supports external table storage")
	}

	version, exists, err := c.tableVersion(name)
	if err != nil {
		c.logger.Error(err.Error())
		return err
	}

	if !exists {
		return fmt.Errorf("InsertTableAsSelect: table %q does not exist", name)
	}

	_, err = c.Execute(ctx, &Statement{
		Query: fmt.Sprintf("INSERT INTO %s.default %s (%s)", safeSQLName(dbName(name, version)), insertByNameClause, sql),
	})
	return err
}

func (c *Connection) updateVersion(name, version string) error {
	pathToFile := filepath.Join(c.config.DBStoragePath, name, "version.txt")
	file, err := os.Create(pathToFile)
	if err != nil {
		return err
	}

	_, err = file.WriteString(version)
	return err
}

func (c *Connection) detachAndRemoveFile(db, dbFile string) {
	_, err := c.Execute(context.Background(), &Statement{Query: fmt.Sprintf("DETACH %s", safeSQLName(db))})
	removeDBFile(dbFile)
	if err != nil {
		c.logger.Error(err.Error())
	}
}

// duckDB raises Contents of view were altered: types don't match! error even when number of columns are same but sequence of column changes in underlying table.
// duckDB raises Contents of view were altered: types don't match! error even when number of columns are same but sequence of column changes in underlying table.
// This causes temporary query failures till the model view is not updated to reflect the new column sequence.
// We ensure that view for external table storage is always generated using a stable order of columns of underlying table.
// Additionally we want to keep the same order as the underlying table locally so that we can show columns in the same order as they appear in source data.
// Using `AllowHostAccess` as proxy to check if we are running in local/cloud mode.
func (c *Connection) generateSelectQuery(ctx context.Context, db string) (string, error) {
	if c.config.AllowHostAccess {
		return fmt.Sprintf("SELECT * FROM %s.default", safeSQLName(db)), nil
	}

	rows, err := c.Execute(ctx, &Statement{
		Query: fmt.Sprintf(`
			SELECT column_name AS name
			FROM information_schema.columns
			WHERE table_catalog = %s AND table_name = 'default'
			ORDER BY name ASC`, safeSQLString(db)),
	})
	if err != nil {
		return "", err
	}
	defer rows.Close()

	cols := make([]string, 0)
	var col string
	for rows.Next() {
		if err := rows.Scan(&col); err != nil {
			return "", err
		}
		cols = append(cols, safeName(col))
	}

	return fmt.Sprintf("SELECT %s FROM %s.default", strings.Join(cols, ", "), safeSQLName(db)), nil
}

func (c *Connection) AddTableColumn(ctx context.Context, tableName, columnName, typ string) error {
	c.logger.Info(fmt.Sprintf("add table column %s %s %s", tableName, columnName, typ))
	if !c.config.ExtTableStorage {
		return fmt.Errorf("gopie supports external storage table only")
	}
	version, exists, err := c.tableVersion(tableName)
	if err != nil {
		return err
	}

	if !exists {
		return fmt.Errorf("table %q does not exist", tableName)
	}

	dbName := dbName(tableName, version)
	_, err = c.Execute(ctx, &Statement{Query: fmt.Sprintf("ALTER TABLE %s.default ADD COLUMN %s %s", safeSQLName(dbName), safeSQLName(columnName), typ)})
	if err != nil {
		return err
	}
	_, err = c.Execute(ctx, &Statement{Query: fmt.Sprintf("CREATE OR REPLACE VIEW %s AS SELECT * FROM %s.default", safeSQLName(tableName), safeSQLName(dbName))})
	if err != nil {
		c.logger.Error(err.Error())
	}
	return err
}

func (c *Connection) AlterTableColumn(ctx context.Context, tableName, columnName, newType string) error {
	c.logger.Info(fmt.Sprintf("alter table column %s %s %s", tableName, columnName, newType))

	if !c.config.ExtTableStorage {
		return fmt.Errorf("gopie supports external storage table only")
	}
	version, exists, err := c.tableVersion(tableName)
	if err != nil {
		return err
	}

	if !exists {
		return fmt.Errorf("table %q does not exist", tableName)
	}

	dbName := dbName(tableName, version)

	_, err = c.Execute(ctx, &Statement{Query: fmt.Sprintf("ALTER TABLE %s.default ALTER %s TYPE %s", safeSQLName(dbName), safeSQLName(columnName), newType)})
	if err != nil {
		c.logger.Error(err.Error())
		return err
	}
	_, err = c.Execute(ctx, &Statement{Query: fmt.Sprintf("CREATE OR REPLACE VIEW %s AS SELECT * FROM %s.default", safeSQLName(tableName), safeSQLName(dbName))})
	if err != nil {
		c.logger.Error(err.Error())
	}
	return err
}

// func (c *Connection) converToEnum(ctx context.Context, table string, cols []string) error {
// 	if len(cols) == 0 {
// 		return fmt.Errorf("empty list")
// 	}
//
// 	if !c.config.ExtTableStorage {
// 		return fmt.Errorf("Gopie only supports external table storage")
// 	}
//
// 	c.logger.Info("convert column to enum %s %s", table, cols)
// 	olderVersoin, exists, err := c.tableVersion(table)
// 	if err != nil {
// 		return err
// 	}
//
// 	if !exists {
// 		return fmt.Errorf("table %q does not exists", table)
// 	}
//
//
// 	res, err := c.Execute(ctx, &Statement{
// 		Query:    "SELECT current_database(), current_schema()",
// 	})
// 	if err != nil {
// 		return err
// 	}
//
// 	var mainDB, mainSchema string
// 	if res.Next() {
// 		if err := res.Scan(&mainDB, &mainSchema); err != nil {
// 			_ = res.Close()
// 			return err
// 		}
// 	}
//
// 	_ = res.Close()
//
// 	sourceDir := filepath.Join(c.config.DBStoragePath, table)
// 	newVersion := fmt.Sprint(time.Now().UnixMilli())
// 	newDBFile := filepath.Join(sourceDir, fmt.Sprintf("%s.db", newVersion))
// 	newDB := dbName(table, newVersion)
//
// 	_, err = c.Execute(ctx, &Statement{Query:fmt.Sprintf("USE %s", safeSQLName(newDB))})
// 	if err != nil {
// 		fmt.Sprintf(err.Error())
// 	}
// }

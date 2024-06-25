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

	"github.com/XSAM/otelsql"
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

var conn *sqlx.Conn

func (c *Connection) Execute(ctx context.Context, stmt *Statement) (res *Result, outErr error) {
	if c.config.LogQueries {
		c.logger.Info("duckdb query: %v, %v", stmt.Query, stmt.Args)
	}

	if conn == nil {
		var err error
		conn, err = c.db.Connx(ctx)
		if err != nil {
			return nil, fmt.Errorf("error create a connection: %s", err.Error())
		}
	}

	rows, err := conn.QueryContext(ctx, stmt.Query, stmt.Args...)
	if err != nil {
		fmt.Println(err.Error())
		return nil, err
	}

	schema, err := RowsToSchema(rows)
	if err != nil {

		return nil, err
	}
	res = &Result{
		Rows:   rows,
		Schema: schema,
	}

	return res, nil
}

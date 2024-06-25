package duckdb

import (
	"context"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/jmoiron/sqlx"
)

var migrationsVersionTable = "gopie.migrations_version"

func (c *Connection) Migrate(ctx context.Context) error {

	if conn == nil {
		var err error
		conn, err = c.db.Connx(ctx)
		if err != nil {
			return fmt.Errorf("error create a connection: %s", err.Error())
		}
	}
	_, err := conn.ExecContext(ctx, "CREATE SCHEMA IF NOT EXISTS gopie")
	if err != nil {
		c.logger.Error(err.Error())
		return err
	}

	_, err = conn.ExecContext(ctx, fmt.Sprintf("create table if not exists %s(version integer not null)", migrationsVersionTable))
	if err != nil {
		c.logger.Error(err.Error())
		return err
	}

	_, err = conn.ExecContext(ctx, fmt.Sprintf("insert into %s(version) select 0 where 0=(select count(*) from %s)", migrationsVersionTable, migrationsVersionTable))
	if err != nil {
		c.logger.Error(err.Error())
		return err
	}

	var currentVersion int
	err = conn.QueryRowContext(ctx, fmt.Sprintf("select version from %s", migrationsVersionTable)).Scan(&currentVersion)
	if err != nil {
		c.logger.Error(err.Error())
		return err
	}

	scripts, err := getMigrationScripts()
	if err != nil {
		c.logger.Error(err.Error())
		return nil
	}
	for name, sql := range scripts {
		version, err := migrationFilenameToVersion(name)
		if err != nil {
			c.logger.Error(err.Error())
			return fmt.Errorf("unexpected migration filename: %s", name)
		}

		if version <= currentVersion {
			continue
		}

		err = c.migrateSingle(ctx, conn, name, sql, version)
		if err != nil {
			c.logger.Error(err.Error())
			return err
		}
	}
	return nil
}

func (c *Connection) migrateSingle(ctx context.Context, conn *sqlx.Conn, name string, sql []byte, version int) error {
	tx, err := conn.BeginTx(ctx, nil)
	if err != nil {
		c.logger.Error(err.Error())
		return err
	}
	defer func() { _ = tx.Rollback() }()

	_, err = tx.ExecContext(ctx, string(sql))
	if err != nil {
		c.logger.Error(err.Error())
		return fmt.Errorf("failt to run migration: %s with sql: %s", name, string(sql))
	}

	_, err = tx.ExecContext(ctx, fmt.Sprintf("UPDATE %s SET version=?", migrationsVersionTable), version)
	if err != nil {
		c.logger.Error(err.Error())
		return err
	}

	err = tx.Commit()
	if err != nil {
		c.logger.Error(err.Error())
		return err
	}

	return nil
}

func migrationFilenameToVersion(name string) (int, error) {
	return strconv.Atoi(strings.Trim(name, ".sql"))
}

func getMigrationScripts() (map[string][]byte, error) {
	dirPath := "./migrations"
	filesContents := map[string][]byte{}
	dir, err := os.Open(dirPath)
	if err != nil {
		return nil, err
	}
	defer dir.Close()

	files, err := dir.ReadDir(-1)
	if err != nil {
		return nil, err
	}

	for _, file := range files {
		filePath := dirPath + "/" + file.Name()
		content, err := os.ReadFile(filePath)
		if err != nil {
			return nil, err
		}
		filesContents[file.Name()] = content
	}

	return filesContents, nil
}

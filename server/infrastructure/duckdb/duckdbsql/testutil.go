package duckdbsql

import (
	"database/sql"
	_ "github.com/marcboeker/go-duckdb/v2"
	"github.com/stretchr/testify/require"
	"testing"
)

// SetupTestDB creates an in-memory DuckDB database connection and loads the json extension.
func SetupTestDB(t *testing.T) *sql.DB {
	db, err := sql.Open("duckdb", "")
	require.NoError(t, err)

	_, err = db.Exec("INSTALL json; LOAD json;")
	require.NoError(t, err)

	return db
}

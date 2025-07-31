package duckdbsql

import (
	databasesql "database/sql"
)

// queryString runs a DuckDB query and returns the result as a scalar string
func queryString(db *databasesql.DB, qry string, args ...any) ([]byte, error) {
	rows, err := query(db, qry, args...)
	if err != nil {
		return nil, err
	}
	defer func() { _ = rows.Close() }()

	var res []byte
	for rows.Next() {
		err := rows.Scan(&res)
		if err != nil {
			return nil, err
		}
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	return res, nil
}

// query runs a DuckDB query
func query(db *databasesql.DB, qry string, args ...any) (*databasesql.Rows, error) {
	return db.Query(qry, args...)
}

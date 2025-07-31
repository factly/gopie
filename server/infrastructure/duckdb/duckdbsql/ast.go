package duckdbsql

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
)

type AST struct {
	db        *sql.DB
	ast       astNode
	rootNodes []*selectNode
}

type selectNode struct {
	ast astNode
}

func Parse(db *sql.DB, sql string) (*AST, error) {
	sqlAst, err := queryString(db, "select json_serialize_sql(?::VARCHAR)::BLOB", sql)
	if err != nil {
		return nil, err
	}

	nativeAst := astNode{}

	decoder := json.NewDecoder(bytes.NewReader(sqlAst))
	decoder.UseNumber()

	err = decoder.Decode(&nativeAst)
	if err != nil {
		return nil, err
	}

	ast := &AST{
		db:        db,
		ast:       nativeAst,
		rootNodes: make([]*selectNode, 0),
	}

	err = ast.traverse()
	if err != nil {
		return nil, err
	}
	return ast, nil
}

// Format normalizes a DuckDB SQL statement
func (a *AST) Format() (string, error) {
	if a.ast == nil {
		return "", fmt.Errorf("calling format on failed parse")
	}

	sql, err := json.Marshal(a.ast)
	if err != nil {
		return "", err
	}
	res, err := queryString(a.db, "SELECT json_deserialize_sql(?::JSON)", string(sql))
	return string(res), err
}

// RewriteLimit rewrites a DuckDB SQL statement to limit the result size
func (a *AST) RewriteLimit(limit, offset int) error {
	if a.ast == nil {
		return fmt.Errorf("calling rewrite on failed parse")
	}

	if len(a.rootNodes) == 0 {
		return nil
	}

	// We only need to add limit to the top level query
	err := a.rootNodes[0].rewriteLimit(limit, offset)
	if err != nil {
		return err
	}

	return nil
}

package duckdb

import (
	"testing"

	pg_query "github.com/pganalyze/pg_query_go/v6"
	"github.com/stretchr/testify/assert"
	"vitess.io/vitess/go/vt/sqlparser"
)

func TestWalkAndQualifyUnqualifiedTablesForPg(t *testing.T) {
	testCases := []struct {
		name           string
		sql            string
		expectedOutput string
	}{
		{
			name:           "Simple SELECT",
			sql:            "SELECT * FROM users",
			expectedOutput: "SELECT * FROM test_schema.users",
		},
		{
			name:           "SELECT with WHERE",
			sql:            "SELECT id, name FROM users WHERE id > 10",
			expectedOutput: "SELECT id, name FROM test_schema.users WHERE id > 10",
		},
		{
			name:           "SELECT with JOIN",
			sql:            "SELECT u.id, o.order_id FROM users u JOIN orders o ON u.id = o.user_id",
			expectedOutput: "SELECT u.id, o.order_id FROM test_schema.users u JOIN test_schema.orders o ON u.id = o.user_id",
		},
		{
			name:           "SELECT with INNER JOIN",
			sql:            "SELECT * FROM users INNER JOIN orders ON users.id = orders.user_id",
			expectedOutput: "SELECT * FROM test_schema.users JOIN test_schema.orders ON users.id = orders.user_id",
		},
		{
			name:           "SELECT with LEFT JOIN",
			sql:            "SELECT * FROM users LEFT JOIN orders ON users.id = orders.user_id",
			expectedOutput: "SELECT * FROM test_schema.users LEFT JOIN test_schema.orders ON users.id = orders.user_id",
		},
		{
			name:           "SELECT with subquery",
			sql:            "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)",
			expectedOutput: "SELECT * FROM test_schema.users WHERE id IN (SELECT user_id FROM test_schema.orders)",
		},
		{
			name:           "SELECT with CTE",
			sql:            "WITH user_orders AS (SELECT * FROM orders) SELECT * FROM users JOIN user_orders ON users.id = user_orders.user_id",
			expectedOutput: "WITH user_orders AS (SELECT * FROM test_schema.orders) SELECT * FROM test_schema.users JOIN test_schema.user_orders ON users.id = user_orders.user_id",
		},
		{
			name:           "SELECT with already qualified table",
			sql:            "SELECT * FROM public.users",
			expectedOutput: "SELECT * FROM public.users",
		},
		{
			name:           "SELECT with mixed qualified and unqualified tables",
			sql:            "SELECT * FROM users JOIN public.orders ON users.id = public.orders.user_id",
			expectedOutput: "SELECT * FROM test_schema.users JOIN public.orders ON users.id = public.orders.user_id",
		},
		{
			name:           "SELECT with multiple JOINs",
			sql:            "SELECT u.id, o.order_id, p.name FROM users u JOIN orders o ON u.id = o.user_id JOIN products p ON o.product_id = p.id",
			expectedOutput: "SELECT u.id, o.order_id, p.name FROM test_schema.users u JOIN test_schema.orders o ON u.id = o.user_id JOIN test_schema.products p ON o.product_id = p.id",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// Parse the input SQL
			result, err := pg_query.Parse(tc.sql)
			assert.NoError(t, err)
			if err != nil {
				return
			}

			// Apply schema qualification
			for _, stmt := range result.Stmts {
				walkAndQualifyUnqualifiedTablesForPg(stmt.Stmt, "test_schema")
			}

			// Get the modified SQL
			outputSQL, err := pg_query.Deparse(result)
			assert.NoError(t, err)
			if err != nil {
				return
			}

			// Verify the result
			assert.Equal(t, tc.expectedOutput, outputSQL)
		})
	}
}

func TestWalkAndQualifyUnqualifiedTablesForMySQL(t *testing.T) {
	testCases := []struct {
		name           string
		sql            string
		expectedOutput string
	}{
		{
			name:           "Simple SELECT",
			sql:            "SELECT * FROM users",
			expectedOutput: "select * from test_schema.users",
		},
		{
			name:           "SELECT with WHERE",
			sql:            "SELECT id, name FROM users WHERE id > 10",
			expectedOutput: "select id, `name` from test_schema.users where id > 10",
		},
		{
			name:           "SELECT with JOIN",
			sql:            "SELECT u.id, o.order_id FROM users u JOIN orders o ON u.id = o.user_id",
			expectedOutput: "select u.id, o.order_id from test_schema.users as u join test_schema.orders as o on u.id = o.user_id",
		},
		{
			name:           "SELECT with INNER JOIN",
			sql:            "SELECT * FROM users INNER JOIN orders ON users.id = orders.user_id",
			expectedOutput: "select * from test_schema.users join test_schema.orders on users.id = orders.user_id",
		},
		{
			name:           "SELECT with LEFT JOIN",
			sql:            "SELECT * FROM users LEFT JOIN orders ON users.id = orders.user_id",
			expectedOutput: "select * from test_schema.users left join test_schema.orders on users.id = orders.user_id",
		},
		{
			name:           "SELECT with subquery",
			sql:            "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)",
			expectedOutput: "select * from test_schema.users where id in (select user_id from test_schema.orders)",
		},
		{
			name:           "SELECT with already qualified table",
			sql:            "SELECT * FROM public.users",
			expectedOutput: "select * from public.users",
		},
		{
			name:           "SELECT with mixed qualified and unqualified tables",
			sql:            "SELECT * FROM users JOIN public.orders ON users.id = public.orders.user_id",
			expectedOutput: "select * from test_schema.users join public.orders on users.id = public.orders.user_id",
		},
		{
			name:           "SELECT with multiple JOINs",
			sql:            "SELECT u.id, o.order_id, p.name FROM users u JOIN orders o ON u.id = o.user_id JOIN products p ON o.product_id = p.id",
			expectedOutput: "select u.id, o.order_id, p.`name` from test_schema.users as u join test_schema.orders as o on u.id = o.user_id join test_schema.products as p on o.product_id = p.id",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// Parse the input SQL using Vitess parser
			parser, _ := sqlparser.New(sqlparser.Options{})
			stmt, err := parser.Parse(tc.sql)
			assert.NoError(t, err)
			if err != nil {
				return
			}

			// Apply schema qualification
			err = WalkAndQualifyUnqualifiedTablesForMySQL(stmt, "test_schema")
			assert.NoError(t, err)

			// Get the modified SQL
			outputSQL := sqlparser.String(stmt)

			// Verify the result
			assert.Equal(t, tc.expectedOutput, outputSQL)
		})
	}
}

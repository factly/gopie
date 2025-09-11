package duckdbsql

import (
	"sort"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestAST_TableNames(t *testing.T) {
	testCases := []struct {
		title         string
		sql           string
		expectedNames []string
	}{
		{
			title:         "Simple Select",
			sql:           "SELECT * FROM users",
			expectedNames: []string{"users"},
		},
		{
			title:         "Select with JOIN",
			sql:           "SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id",
			expectedNames: []string{"orders", "users"},
		},
		{
			title:         "Select with multiple JOINs",
			sql:           "SELECT p.name, c.name, s.name FROM products p JOIN categories c ON p.cat_id = c.id JOIN suppliers s ON p.sup_id = s.id",
			expectedNames: []string{"categories", "products", "suppliers"},
		},
		{
			title:         "Query with CTE",
			sql:           "WITH recent_orders AS (SELECT * FROM orders WHERE order_date > '2024-01-01') SELECT * FROM recent_orders ro JOIN customers c ON ro.customer_id = c.id",
			expectedNames: []string{"customers", "orders"},
		},
		{
			title:         "Query with Subquery",
			sql:           "SELECT name FROM (SELECT * FROM employees WHERE department = 'Sales')",
			expectedNames: []string{"employees"},
		},
		{
			title:         "Complex Query",
			sql:           "WITH cte AS (SELECT id FROM source_tbl) SELECT c.name FROM customers c JOIN (SELECT * FROM orders WHERE amount > 100) AS big_orders ON c.id = big_orders.customer_id",
			expectedNames: []string{"customers", "orders", "source_tbl"},
		},
		{
			title:         "Union Query",
			sql:           "SELECT name FROM table1 UNION ALL SELECT name FROM table2",
			expectedNames: []string{"table1", "table2"},
		},
		{
			title:         "No Tables",
			sql:           "SELECT 1",
			expectedNames: []string{},
		},
	}

	for _, tc := range testCases {
		t.Run(tc.title, func(t *testing.T) {
			db := setupDB(t)
			defer db.Close()

			ast, err := Parse(db, tc.sql)
			require.NoError(t, err)

			actualNames, err := ast.TableNames()
			require.NoError(t, err)

			sort.Strings(actualNames)
			sort.Strings(tc.expectedNames)

			require.Equal(t, tc.expectedNames, actualNames)
		})
	}
}

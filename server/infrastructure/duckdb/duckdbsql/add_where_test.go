package duckdbsql

import (
	"testing"

	_ "github.com/marcboeker/go-duckdb/v2" // DuckDB driver
	"github.com/stretchr/testify/require"
)

func TestAST_AddWhere(t *testing.T) {
	testCases := []struct {
		title            string
		sql              string
		conditionToAdd   string
		expectedFinalSql string
	}{
		{
			title:            "Add_Where_To_Simple_Select",
			sql:              "SELECT * FROM tbl",
			conditionToAdd:   "id > 10",
			expectedFinalSql: "SELECT * FROM tbl WHERE (id > 10)",
		},
		{
			title:            "Add_Where_To_Existing_Where",
			sql:              "SELECT col1 FROM tbl WHERE col1 = 'test'",
			conditionToAdd:   "col2 IS NOT NULL",
			expectedFinalSql: "SELECT col1 FROM tbl WHERE ((col1 = 'test') AND (col2 IS NOT NULL))",
		},
		{
			title:            "Add_Where_With_Quoted_Identifiers",
			sql:              `SELECT "My Column" FROM "My Table"`,
			conditionToAdd:   `"Another Column" = 5`,
			expectedFinalSql: `SELECT "My Column" FROM "My Table" WHERE ("Another Column" = 5)`,
		},
		{
			title:            "Add_Complex_Where_To_Existing_Where",
			sql:              "SELECT * FROM sales WHERE region = 'North'",
			conditionToAdd:   "(amount > 1000 OR status = 'Urgent')",
			expectedFinalSql: "SELECT * FROM sales WHERE ((region = 'North') AND ((amount > 1000) OR (status = 'Urgent')))",
		},
		{
			title:          "Add_Where_To_Query_With_Join_And_Limit",
			sql:            "SELECT o.id, c.name FROM orders o JOIN customers c ON o.cust_id = c.id LIMIT 100",
			conditionToAdd: `o.order_date > '2024-01-01'`,
			// Note: DuckDB may quote "name" as c."name" in output
			expectedFinalSql: `SELECT o.id, c."name" FROM orders AS o INNER JOIN customers AS c ON ((o.cust_id = c.id)) WHERE (o.order_date > '2024-01-01') LIMIT 100`,
		},
		{
			title:            "Add_Where_To_CTE",
			sql:              "WITH cte AS (SELECT id FROM source_tbl) SELECT id FROM cte",
			conditionToAdd:   `id < 50`,
			expectedFinalSql: `WITH cte AS (SELECT id FROM source_tbl)SELECT id FROM cte WHERE (id < 50)`,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.title, func(t *testing.T) {
			db := SetupTestDB(t)
			defer db.Close()

			ast, err := Parse(db, tc.sql)
			require.NoError(t, err)
			require.NotNil(t, ast)

			err = ast.AddWhere(tc.conditionToAdd)
			require.NoError(t, err)

			actualSql, err := ast.Format()
			require.NoError(t, err)

			require.Equal(t, tc.expectedFinalSql, actualSql)
		})
	}
}

func TestAST_SetSelectList(t *testing.T) {
	testCases := []struct {
		title            string
		sql              string
		columnsToSet     string
		expectedFinalSql string
	}{
		{
			title:            "Replace_Star_With_Columns",
			sql:              "SELECT * FROM tbl WHERE id = 1",
			columnsToSet:     "col1, col2",
			expectedFinalSql: "SELECT col1, col2 FROM tbl WHERE (id = 1)",
		},
		{
			title:        "Replace_Columns_With_Star",
			sql:          "SELECT name, email FROM users ORDER BY name",
			columnsToSet: "*",
			// Note: DuckDB may quote "name" in ORDER BY
			expectedFinalSql: `SELECT * FROM users ORDER BY "name"`,
		},
		{
			title:        "Replace_Columns_With_Different_Columns",
			sql:          "SELECT a, b, c FROM data LIMIT 10",
			columnsToSet: `"x" AS alias_x, y`,
			// Note: DuckDB may quote "data" table name
			expectedFinalSql: `SELECT x AS alias_x, y FROM "data" LIMIT 10`,
		},
		{
			title:        "Set_Single_Column",
			sql:          "SELECT * FROM products WHERE active = true",
			columnsToSet: "product_id",
			// Note: DuckDB may cast boolean literals
			expectedFinalSql: `SELECT product_id FROM products WHERE (active = CAST('t' AS BOOLEAN))`,
		},
		{
			title:            "Set_Expression_Column",
			sql:              "SELECT name FROM employees",
			columnsToSet:     "salary * 1.1 AS increased_salary",
			expectedFinalSql: "SELECT (salary * 1.1) AS increased_salary FROM employees",
		},
		{
			title:            "Set_Columns_In_CTE",
			sql:              "WITH cte AS (SELECT a, b FROM source) SELECT a FROM cte",
			columnsToSet:     "b", // Setting select list for the main query, not CTE
			expectedFinalSql: "WITH cte AS (SELECT a, b FROM source)SELECT b FROM cte",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.title, func(t *testing.T) {
			db := SetupTestDB(t)
			defer db.Close()

			ast, err := Parse(db, tc.sql)
			require.NoError(t, err)
			require.NotNil(t, ast)

			err = ast.SetSelectList(tc.columnsToSet)
			require.NoError(t, err)

			actualSql, err := ast.Format()
			require.NoError(t, err)

			require.Equal(t, tc.expectedFinalSql, actualSql)
		})
	}
}

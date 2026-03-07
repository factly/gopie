package duckdbsql

import (
	"testing"

	_ "github.com/marcboeker/go-duckdb/v2"
	"github.com/stretchr/testify/require"
)

func TestAST_QualifyUnqualifiedTables(t *testing.T) {
	testCases := []struct {
		title       string
		sql         string
		schemaName  string
		expectedSql string
	}{
		{
			title:       "Simple_Select_Table",
			sql:         "SELECT * FROM users",
			schemaName:  "public",
			expectedSql: "SELECT * FROM \"public\".\"users\"",
		},
		{
			title:       "Select_With_Join_Unqualified",
			sql:         "SELECT a.*, b.* FROM users a JOIN roles b ON a.role_id = b.id",
			schemaName:  "public",
			expectedSql: "SELECT a.*, b.* FROM \"public\".\"users\" AS a INNER JOIN \"public\".\"roles\" AS b ON ((a.role_id = b.id))",
		},
		{
			title:       "With_Clause_CTE_Should_Not_Qualify_CTE_Reference",
			sql:         "WITH mycte AS (SELECT id FROM users) SELECT * FROM mycte",
			schemaName:  "myschema",
			expectedSql: "WITH mycte AS (SELECT id FROM \"myschema\".\"users\") SELECT * FROM mycte",
		},
	}

	testCases = append(testCases, []struct {
		title       string
		sql         string
		schemaName  string
		expectedSql string
	}{
		{
			title:       "Nested_Subquery_Unqualified",
			sql:         "SELECT * FROM (SELECT * FROM orders WHERE user_id IN (SELECT id FROM users)) subq",
			schemaName:  "sales",
			expectedSql: "SELECT * FROM (SELECT * FROM \"sales\".\"orders\" WHERE (user_id IN (SELECT id FROM \"sales\".\"users\"))) AS subq",
		},
		{
			title:       "Multiple_Joins_Mixed_Qualification",
			sql:         "SELECT * FROM users u JOIN public.roles r ON u.role_id = r.id JOIN permissions p ON r.id = p.role_id",
			schemaName:  "app",
			expectedSql: "SELECT * FROM \"app\".\"users\" AS u INNER JOIN \"app\".public.roles AS r ON ((u.role_id = r.id)) INNER JOIN \"app\".\"permissions\" AS p ON ((r.id = p.role_id))",
		},
		{
			title:       "CTE_And_Subquery_Mixed",
			sql:         "WITH c1 AS (SELECT * FROM orders) SELECT * FROM c1 WHERE id IN (SELECT order_id FROM items)",
			schemaName:  "main",
			expectedSql: "WITH c1 AS (SELECT * FROM \"main\".\"orders\") SELECT * FROM c1 WHERE (id IN (SELECT order_id FROM \"main\".\"items\"))",
		},
		{
			title:       "Alias_And_Schema_Qualification",
			sql:         "SELECT u.id, r.name FROM users u LEFT JOIN roles r ON u.role_id = r.id",
			schemaName:  "auth",
			expectedSql: "SELECT u.id, r.name FROM \"auth\".\"users\" AS u LEFT JOIN \"auth\".\"roles\" AS r ON ((u.role_id = r.id))",
		},
		{
			title:       "CTE_Qualified_Table_Ref",
			sql:         "WITH cte AS (SELECT * FROM public.orders) SELECT * FROM cte",
			schemaName:  "main",
			expectedSql: "WITH cte AS (SELECT * FROM \"main\".public.orders) SELECT * FROM cte",
		},
		{
			title:       "Schema_Qualified_Table_Gets_Catalog_Prefix",
			sql:         "SELECT * FROM analysis.sales",
			schemaName:  "pg_ext_abc",
			expectedSql: "SELECT * FROM \"pg_ext_abc\".analysis.sales",
		},
	}...)

	for _, tc := range testCases {
		t.Run(tc.title, func(t *testing.T) {
			db := SetupTestDB(t)
			defer db.Close()

			// 1. Parse the SQL to get the AST
			ast, err := Parse(db, tc.sql)
			require.NoError(t, err)
			require.NotNil(t, ast)

			// 2. Qualify unqualified tables
			err = ast.QualifyUnqualifiedTables(tc.schemaName)
			require.NoError(t, err)

			// 3. Format the AST back to SQL
			actualSql, err := ast.Format()
			require.NoError(t, err)

			// 4. Assert output SQL matches expected
			require.Equal(t, tc.expectedSql, actualSql)
		})
	}

}

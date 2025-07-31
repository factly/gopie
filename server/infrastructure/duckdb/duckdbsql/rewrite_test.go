package duckdbsql

import (
	"database/sql"
	"testing"

	_ "github.com/marcboeker/go-duckdb/v2"
	"github.com/stretchr/testify/require"
)

// setupDB creates an in-memory DuckDB database connection for testing.
// It ensures the 'json' extension is loaded, which is required for the parser.
func setupDB(t *testing.T) *sql.DB {
	db, err := sql.Open("duckdb", "")
	require.NoError(t, err)

	_, err = db.Exec("INSTALL json; LOAD json;")
	require.NoError(t, err)

	return db
}

func TestAST_RewriteLimit(t *testing.T) {
	// Test cases covering various SQL query structures and rewrite scenarios.
	testCases := []struct {
		title       string
		sql         string
		limit       int
		offset      int
		expectedSql string
	}{
		// --- Simple SELECT Statements ---
		{
			title:       "Simple_Select_Add_Limit_Only",
			sql:         "SELECT * FROM tbl",
			limit:       100,
			offset:      0,
			expectedSql: "SELECT * FROM tbl LIMIT 100",
		},
		{
			title:       "Simple_Select_Add_Limit_And_Offset",
			sql:         "SELECT * FROM tbl",
			limit:       50,
			offset:      25,
			expectedSql: "SELECT * FROM tbl LIMIT 50 OFFSET 25",
		},
		{
			title:       "Simple_Select_Update_Existing_Limit_(New_Is_Smaller)",
			sql:         "SELECT * FROM tbl LIMIT 1000",
			limit:       200,
			offset:      0,
			expectedSql: "SELECT * FROM tbl LIMIT 200",
		},
		{
			title:       "Simple_Select_Update_Limit_And_Add_Offset",
			sql:         "SELECT * FROM tbl LIMIT 1000",
			limit:       150, // Smaller, so update
			offset:      30,  // Doesn't exist, so add
			expectedSql: "SELECT * FROM tbl LIMIT 150 OFFSET 30",
		},
		{
			title:       "Simple_Select_Update_Limit_But_Keep_Existing_Offset",
			sql:         "SELECT * FROM tbl LIMIT 1000 OFFSET 100",
			limit:       500, // Smaller, so update
			offset:      50,  // Exists, so DO NOT update
			expectedSql: "SELECT * FROM tbl LIMIT 500 OFFSET 100",
		},
		{
			title:       "Simple_Select_Do_Not_Update_Limit_(New_Is_Larger)",
			sql:         "SELECT * FROM tbl LIMIT 75",
			limit:       100, // Larger, so DO NOT update
			offset:      10,  // Doesn't exist, so add
			expectedSql: "SELECT * FROM tbl LIMIT 75 OFFSET 10",
		},
		{
			title:       "Simple_Select_Do_Not_Update_Anything",
			sql:         "SELECT * FROM tbl LIMIT 75 OFFSET 100",
			limit:       100, // Larger, so DO NOT update
			offset:      50,  // Exists, so DO NOT update
			expectedSql: "SELECT * FROM tbl LIMIT 75 OFFSET 100",
		},

		// --- Queries with WITH Clause (CTE) ---
		{
			title:       "With_Clause_Add_Limit_And_Offset",
			sql:         "WITH cte AS (SELECT id FROM source_tbl) SELECT id FROM cte WHERE id > 10",
			limit:       80,
			offset:      40,
			expectedSql: "WITH cte AS (SELECT id FROM source_tbl)SELECT id FROM cte WHERE (id > 10) LIMIT 80 OFFSET 40",
		},
		{
			title:       "With_Clause_Update_Existing_Limit",
			sql:         "WITH cte AS (SELECT id FROM source_tbl) SELECT id FROM cte LIMIT 500",
			limit:       99,
			offset:      0,
			expectedSql: "WITH cte AS (SELECT id FROM source_tbl)SELECT id FROM cte LIMIT 99",
		},

		// --- Queries with UNION ---
		{
			title:       "Union_All_Add_Limit_And_Offset",
			sql:         "SELECT id FROM tbl1 UNION ALL SELECT id FROM tbl2",
			limit:       25,
			offset:      10,
			expectedSql: "(SELECT id FROM tbl1) UNION ALL (SELECT id FROM tbl2) LIMIT 25 OFFSET 10",
		},
		{
			title:       "Union_All_Update_Existing_Limit",
			sql:         "SELECT id FROM tbl1 UNION ALL SELECT id FROM tbl2 LIMIT 200",
			limit:       50,
			offset:      0,
			expectedSql: "(SELECT id FROM tbl1) UNION ALL (SELECT id FROM tbl2) LIMIT 50",
		},

		// --- Complex Queries ---
		{
			title: "Complex_Query_Add_Limit_And_Offset",
			sql: `
				WITH regional_sales AS (
					SELECT region, SUM(amount) AS total_sales
					FROM orders
					GROUP BY region
				)
				SELECT o.order_id, c.customer_name, rs.total_sales
				FROM orders AS o
				JOIN customers AS c ON o.customer_id = c.id
				JOIN regional_sales AS rs ON o.region = rs.region
				WHERE o.order_date > '2024-01-01'
				ORDER BY o.order_date DESC
			`,
			limit:       50,
			offset:      10,
			expectedSql: "WITH regional_sales AS (SELECT region, sum(amount) AS total_sales FROM orders GROUP BY region)SELECT o.order_id, c.customer_name, rs.total_sales FROM orders AS o INNER JOIN customers AS c ON ((o.customer_id = c.id)) INNER JOIN regional_sales AS rs ON ((o.region = rs.region)) WHERE (o.order_date > '2024-01-01') ORDER BY o.order_date DESC LIMIT 50 OFFSET 10",
		},
		{
			title: "Complex_Query_Update_Limit_Keep_Offset",
			sql: `
				WITH regional_sales AS (
					SELECT region, SUM(amount) AS total_sales
					FROM orders
					GROUP BY region
				)
				SELECT o.order_id, c.customer_name, rs.total_sales
				FROM orders AS o
				JOIN customers AS c ON o.customer_id = c.id
				JOIN regional_sales AS rs ON o.region = rs.region
				WHERE o.order_date > '2024-01-01'
				ORDER BY o.order_date DESC
				LIMIT 1000 OFFSET 200
			`,
			limit:       25, // Smaller, so update
			offset:      5,  // Exists, so DO NOT update
			expectedSql: "WITH regional_sales AS (SELECT region, sum(amount) AS total_sales FROM orders GROUP BY region)SELECT o.order_id, c.customer_name, rs.total_sales FROM orders AS o INNER JOIN customers AS c ON ((o.customer_id = c.id)) INNER JOIN regional_sales AS rs ON ((o.region = rs.region)) WHERE (o.order_date > '2024-01-01') ORDER BY o.order_date DESC LIMIT 25 OFFSET 200",
		},
	}

	// Run test cases
	for _, tc := range testCases {
		t.Run(tc.title, func(t *testing.T) {
			// Setup a fresh DB connection for each test to ensure isolation.
			db := setupDB(t)
			defer db.Close()

			// 1. Parse the SQL to get the AST
			ast, err := Parse(db, tc.sql)
			require.NoError(t, err)
			require.NotNil(t, ast)

			// 2. Rewrite the LIMIT and OFFSET
			err = ast.RewriteLimit(tc.limit, tc.offset)
			require.NoError(t, err)

			// 3. Format the AST back to a SQL string
			actualSql, err := ast.Format()
			require.NoError(t, err)

			// 4. Verify the output
			require.Equal(t, tc.expectedSql, actualSql)
		})
	}
}

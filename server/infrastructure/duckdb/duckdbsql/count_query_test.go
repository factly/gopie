package duckdbsql

import (
	"database/sql"
	"testing"

	_ "github.com/marcboeker/go-duckdb/v2"
	"github.com/stretchr/testify/require"
)

// setupTestDB now only installs the required 'json' extension.
// No table creation is needed.
func setupTestDB(t *testing.T) *sql.DB {
	db, err := sql.Open("duckdb", "")
	require.NoError(t, err)

	_, err = db.Exec("INSTALL json; LOAD json;")
	require.NoError(t, err)

	return db
}

func TestAST_ToCountQuery(t *testing.T) {
	testCases := []struct {
		title       string
		sql         string
		expectedSql string
	}{
		{
			title:       "Simple_Select",
			sql:         "SELECT * FROM tbl",
			expectedSql: "SELECT count(*) FROM (SELECT * FROM tbl)",
		},
		{
			title:       "Select_With_Where_Clause",
			sql:         "SELECT col1, col2 FROM tbl WHERE col1 > 100",
			expectedSql: "SELECT count(*) FROM (SELECT col1, col2 FROM tbl WHERE (col1 > 100))",
		},
		{
			title:       "Select_With_Order_By_And_Limit",
			sql:         "SELECT * FROM tbl WHERE id = 1 ORDER BY name ASC LIMIT 50 OFFSET 10",
			expectedSql: "SELECT count(*) FROM (SELECT * FROM tbl WHERE (id = 1) LIMIT 50 OFFSET 10)",
		},
		{
			title:       "Select_With_Limit_Only",
			sql:         "SELECT * FROM gp_GAYulCGSRMkNV LIMIT 1000",
			expectedSql: "SELECT count(*) FROM (SELECT * FROM gp_GAYulCGSRMkNV LIMIT 1000)",
		},
		{
			title:       "Select_With_Group_By",
			sql:         "SELECT region, COUNT(*) FROM sales GROUP BY region",
			expectedSql: "SELECT count(*) FROM (SELECT region, count_star() FROM sales GROUP BY region)",
		},
		{
			title:       "With_Clause_Simple",
			sql:         "WITH cte AS (SELECT id FROM source_tbl) SELECT id FROM cte",
			expectedSql: "SELECT count(*) FROM (WITH cte AS (SELECT id FROM source_tbl)SELECT id FROM cte)",
		},
		{
			title:       "Union_All_With_Limit_And_Order_By",
			sql:         "SELECT id FROM tbl1 UNION ALL SELECT id FROM tbl2 ORDER BY id LIMIT 100",
			expectedSql: "SELECT count(*) FROM ((SELECT id FROM tbl1) UNION ALL (SELECT id FROM tbl2) LIMIT 100)",
		},
		{
			title: "Complex_Query_With_Joins_And_CTE",
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
			expectedSql: "SELECT count(*) FROM (WITH regional_sales AS (SELECT region, sum(amount) AS total_sales FROM orders GROUP BY region)SELECT o.order_id, c.customer_name, rs.total_sales FROM orders AS o INNER JOIN customers AS c ON ((o.customer_id = c.id)) INNER JOIN regional_sales AS rs ON ((o.region = rs.region)) WHERE (o.order_date > '2024-01-01'))",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.title, func(t *testing.T) {
			db := setupTestDB(t)
			defer db.Close()

			ast, err := Parse(db, tc.sql)
			require.NoError(t, err)
			require.NotNil(t, ast)

			actualSql, err := ast.ToCountQuery()
			require.NoError(t, err)

			// The only validation needed is to compare the generated string.
			require.Equal(t, tc.expectedSql, actualSql)
		})
	}
}

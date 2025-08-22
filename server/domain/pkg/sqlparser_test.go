package pkg

import (
	"testing"
)

func TestIsReadOnlyQuery(t *testing.T) {
	tests := []struct {
		name     string
		query    string
		expected bool
	}{
		// Valid read-only queries
		{"SELECT statement", "SELECT * FROM users", true},
		{"SELECT with WHERE", "SELECT id, name FROM users WHERE age > 18", true},
		{"WITH CTE", "WITH cte AS (SELECT * FROM users) SELECT * FROM cte", true},
		{"DESCRIBE statement", "DESCRIBE users", true},
		{"DESCRIBE with quotes", "DESCRIBE gp_SF6L9R2JBPU6K", true},
		// DuckDB SUMMARIZE - statistical analysis (read-only)
		{"SUMMARIZE table", "SUMMARIZE users", true},
		{"SUMMARIZE with quotes", "SUMMARIZE gp_SF6L9R2JBPU6K", true},
		{"SUMMARIZE subquery", "SUMMARIZE (SELECT * FROM users WHERE age > 18)", true},
		{"SUMMARIZE SELECT", "SUMMARIZE SELECT * FROM users", true},
		{"Case insensitive SUMMARIZE", "summarize users", true},
		// SHOW queries are now blocked to prevent listing all tables
		{"SHOW statement", "SHOW TABLES", false},
		{"SHOW databases", "SHOW DATABASES", false},
		// EXPLAIN and PRAGMA queries are now blocked for security
		{"EXPLAIN query", "EXPLAIN SELECT * FROM users", false},
		{"PRAGMA table_info", "PRAGMA TABLE_INFO(users)", false},
		// PRAGMA SHOW also blocked
		{"PRAGMA show", "PRAGMA SHOW_TABLES", false},
		{"Case insensitive SELECT", "select * from users", true},
		{"Case insensitive DESCRIBE", "describe users", true},
		{"Leading whitespace", "  SELECT * FROM users", true},
		
		// Invalid (non-read-only) queries - should return false
		{"INSERT statement", "INSERT INTO users VALUES (1, 'John')", false},
		{"UPDATE statement", "UPDATE users SET name = 'Jane' WHERE id = 1", false},
		{"DELETE statement", "DELETE FROM users WHERE id = 1", false},
		{"DROP TABLE", "DROP TABLE users", false},
		{"CREATE TABLE", "CREATE TABLE users (id INT, name VARCHAR)", false},
		{"ALTER TABLE", "ALTER TABLE users ADD COLUMN age INT", false},
		{"TRUNCATE", "TRUNCATE TABLE users", false},
		{"GRANT", "GRANT SELECT ON users TO user1", false},
		{"REVOKE", "REVOKE SELECT ON users FROM user1", false},
		{"MERGE", "MERGE INTO users USING ...", false},
		{"COPY", "COPY users FROM 'file.csv'", false},
		{"SET", "SET search_path = public", false},
		{"BEGIN", "BEGIN TRANSACTION", false},
		{"COMMIT", "COMMIT", false},
		{"ROLLBACK", "ROLLBACK", false},
		
		// Edge cases
		{"Empty query", "", false},
		{"Just whitespace", "   ", false},
		{"Malicious - looks like SELECT but isn't", "SELECTED_FOR_UPDATE", false},
		{"SQL injection attempt", "'; DROP TABLE users; --", false},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := IsReadOnlyQuery(tt.query)
			if result != tt.expected {
				t.Errorf("IsReadOnlyQuery(%q) = %v, want %v", tt.query, result, tt.expected)
			}
		})
	}
}

func TestHasMultipleStatements(t *testing.T) {
	tests := []struct {
		name     string
		query    string
		expected bool
	}{
		{"Single SELECT", "SELECT * FROM users", false},
		{"Single SELECT with semicolon", "SELECT * FROM users;", false},
		{"Multiple statements", "SELECT * FROM users; DROP TABLE users", true},
		{"Multiple SELECTs", "SELECT * FROM users; SELECT * FROM posts", true},
		{"With newlines", "SELECT * FROM users;\nSELECT * FROM posts", true},
		{"DESCRIBE then SELECT", "DESCRIBE users; SELECT * FROM users", true},
		{"Single DESCRIBE", "DESCRIBE users", false},
		{"Single SHOW", "SHOW TABLES", false}, // SHOW is now blocked
		{"Single SUMMARIZE", "SUMMARIZE users", false},
		{"SUMMARIZE then DROP", "SUMMARIZE users; DROP TABLE users", true},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := HasMultipleStatements(tt.query)
			if err != nil {
				t.Fatalf("HasMultipleStatements(%q) returned error: %v", tt.query, err)
			}
			if result != tt.expected {
				t.Errorf("HasMultipleStatements(%q) = %v, want %v", tt.query, result, tt.expected)
			}
		})
	}
}
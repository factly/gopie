package duckdb

import (
	"errors"
	"fmt"
	"net/url"
	"regexp"
	"strings"

	"github.com/marcboeker/go-duckdb/v2"
)

// Compile regex patterns once at package level for better performance
var (
	didYouMeanRegex            = regexp.MustCompile(`(?i)\s*Did you mean "[^"]+"\??`)
	didYouMeanSingleQuoteRegex = regexp.MustCompile(`(?i)\s*Did you mean '[^']+'\??`)
	didYouMeanNoQuotesRegex    = regexp.MustCompile(`(?i)\s*Did you mean \S+\??`)
	candidateTablesRegex       = regexp.MustCompile(`(?i)\s*Candidate tables:.*`)
	whitespaceRegex            = regexp.MustCompile(`\s+`)
)

// parseError formats errors from DuckDB operations, sanitizing sensitive information.
func parseError(err error) error {
	if err == nil {
		return nil
	}

	var duckErr *duckdb.Error
	if errors.As(err, &duckErr) {
		// Sanitize the error message to remove table name suggestions
		sanitizedMsg := sanitizeErrorMessage(err.Error())
		return fmt.Errorf("DuckDB %v error: %s", duckErr.Type, sanitizedMsg)
	}

	// Also sanitize non-DuckDB errors in case they contain suggestions
	return fmt.Errorf("%s", sanitizeErrorMessage(err.Error()))
}

// sanitizeErrorMessage removes table name suggestions from DuckDB error messages
// to prevent exposing potentially sensitive table names to users
func sanitizeErrorMessage(msg string) string {
	// Remove "Did you mean" suggestions that expose table names
	// Pattern: Did you mean "table_name"?
	msg = didYouMeanRegex.ReplaceAllString(msg, "")

	// Remove "Did you mean" with single quotes
	msg = didYouMeanSingleQuoteRegex.ReplaceAllString(msg, "")

	// Remove suggestions without quotes
	msg = didYouMeanNoQuotesRegex.ReplaceAllString(msg, "")

	// Remove "Candidate tables:" followed by table list
	msg = candidateTablesRegex.ReplaceAllString(msg, "")

	// Clean up any double spaces or trailing spaces that might be left
	msg = whitespaceRegex.ReplaceAllString(msg, " ")
	msg = strings.TrimSpace(msg)

	return msg
}

// parseMySQLConnectionString parses different formats of MySQL connection strings
// into a format compatible with the DuckDB MySQL extension.
func parseMySQLConnectionString(connectionString string) (string, error) {
	// Handle mysql:// protocol format
	if strings.HasPrefix(connectionString, "mysql://") {
		u, err := url.Parse(connectionString)
		if err != nil {
			return "", fmt.Errorf("invalid MySQL connection string: %w", err)
		}

		password, _ := u.User.Password()
		username := u.User.Username()
		host := u.Hostname()
		port := u.Port()
		if port == "" {
			port = "3306" // Default MySQL port
		}

		database := strings.TrimPrefix(u.Path, "/")

		// Construct DuckDB MySQL connection format
		dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s database=%s",
			host, port, username, password, database)

		// Add query parameters if any
		if u.RawQuery != "" {
			params, err := url.ParseQuery(u.RawQuery)
			if err == nil {
				for key, values := range params {
					if len(values) > 0 {
						dsn += fmt.Sprintf(" %s=%s", key, values[0])
					}
				}
			}
		}

		return dsn, nil
	}

	// Handle username:password@tcp(host:port)/database format
	if strings.Contains(connectionString, "@tcp(") {
		// Split by @ to separate credentials and connection info
		parts := strings.SplitN(connectionString, "@", 2)
		if len(parts) != 2 {
			return "", fmt.Errorf("invalid MySQL connection string format")
		}

		credentials := parts[0]
		connInfo := parts[1]

		// Extract username and password
		credParts := strings.SplitN(credentials, ":", 2)
		username := credParts[0]
		password := ""
		if len(credParts) > 1 {
			password = credParts[1]
		}

		// Extract host, port, database
		tcpPart := strings.SplitN(connInfo, ")/", 2)
		if len(tcpPart) != 2 {
			return "", fmt.Errorf("invalid MySQL connection string format")
		}

		hostPort := strings.TrimPrefix(tcpPart[0], "tcp(")
		hostPortParts := strings.SplitN(hostPort, ":", 2)
		host := hostPortParts[0]
		port := "3306"
		if len(hostPortParts) > 1 {
			port = hostPortParts[1]
		}

		// Extract database and parameters
		dbAndParams := strings.SplitN(tcpPart[1], "?", 2)
		database := dbAndParams[0]

		// Construct DuckDB MySQL connection format
		dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s database=%s",
			host, port, username, password, database)

		// Add query parameters if any
		if len(dbAndParams) > 1 {
			params, err := url.ParseQuery(dbAndParams[1])
			if err == nil {
				for key, values := range params {
					if len(values) > 0 {
						dsn += fmt.Sprintf(" %s=%s", key, values[0])
					}
				}
			}
		}

		return dsn, nil
	}

	// Handle username:password@hostname:port/database format
	if strings.Contains(connectionString, "@") && !strings.Contains(connectionString, "://") {
		// Split by @ to separate credentials and connection info
		parts := strings.SplitN(connectionString, "@", 2)
		if len(parts) != 2 {
			return "", fmt.Errorf("invalid MySQL connection string format")
		}

		credentials := parts[0]
		connInfo := parts[1]

		// Extract username and password
		credParts := strings.SplitN(credentials, ":", 2)
		username := credParts[0]
		password := ""
		if len(credParts) > 1 {
			password = credParts[1]
		}

		// Extract host, port, database
		hostPortDB := strings.SplitN(connInfo, "/", 2)
		if len(hostPortDB) != 2 {
			return "", fmt.Errorf("invalid MySQL connection string format")
		}

		hostPort := hostPortDB[0]
		hostPortParts := strings.SplitN(hostPort, ":", 2)
		host := hostPortParts[0]
		port := "3306"
		if len(hostPortParts) > 1 {
			port = hostPortParts[1]
		}

		// Extract database and parameters
		dbAndParams := strings.SplitN(hostPortDB[1], "?", 2)
		database := dbAndParams[0]

		// Construct DuckDB MySQL connection format
		dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s database=%s",
			host, port, username, password, database)

		// Add query parameters if any
		if len(dbAndParams) > 1 {
			params, err := url.ParseQuery(dbAndParams[1])
			if err == nil {
				for key, values := range params {
					if len(values) > 0 {
						dsn += fmt.Sprintf(" %s=%s", key, values[0])
					}
				}
			}
		}

		return dsn, nil
	}

	// Already in key=value format for DuckDB MySQL connection
	if strings.Contains(connectionString, "host=") && strings.Contains(connectionString, "user=") {
		return connectionString, nil
	}

	return "", fmt.Errorf("unsupported MySQL connection string format")
}

// maskPasswordInConnectionString replaces the password in a connection string with asterisks
func maskPasswordInConnectionString(connStr string) string {
	if strings.Contains(connStr, "password=") {
		re := regexp.MustCompile(`password=([^ ]*)`)
		return re.ReplaceAllString(connStr, "password=********")
	}
	return connStr
}

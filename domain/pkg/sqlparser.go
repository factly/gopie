package pkg

import (
	"fmt"
	"strconv"

	"github.com/factly/gopie/domain"
	"github.com/xwb1989/sqlparser"
)

// IsSelectStatement checks if the given query is a valid SELECT statement.
// Returns true if it is a SELECT statement, false otherwise.
// Returns an error if the query is invalid or not a SELECT statement.
func IsSelectStatement(query string) (bool, error) {
	stmt, err := sqlparser.Parse(query)
	if err != nil {
		return false, domain.ErrInvalidQuery
	}
	_, isSelect := stmt.(*sqlparser.Select)
	return isSelect, nil
}

// HasMultipleStatements checks if the query contains multiple SQL statements.
// Returns true if multiple statements are found, false otherwise.
// Returns an error if the query is invalid.
func HasMultipleStatements(query string) (bool, error) {
	// Try to get the first statement and remainder
	firstStmt, remainder, err := sqlparser.SplitStatement(query)
	if err != nil {
		return false, domain.ErrInvalidQuery
	}

	// Validate that the first statement is parseable
	_, err = sqlparser.Parse(firstStmt)
	if err != nil {
		return false, domain.ErrInvalidQuery
	}

	// Check if there's any remainder after the first statement
	// If remainder is not empty, we have multiple statements
	return remainder != "", nil
}

// ImposeLimits adds a LIMIT clause if missing or validates existing LIMIT
// against the default limit. If existing LIMIT exceeds default, uses default instead.
// Returns modified query and error if any.
func ImposeLimits(query string, defaultLimit int) (string, error) {
	// Parse the query
	stmt, err := sqlparser.Parse(query)
	if err != nil {
		return "", domain.ErrInvalidQuery
	}

	// Check if it's a SELECT statement
	selectStmt, ok := stmt.(*sqlparser.Select)
	if !ok {
		return "", domain.ErrInvalidQuery
	}

	if selectStmt.Limit == nil {
		// No LIMIT clause exists, add default limit
		selectStmt.Limit = &sqlparser.Limit{
			Rowcount: sqlparser.NewIntVal([]byte(fmt.Sprintf("%d", defaultLimit))),
		}
	} else {
		// LIMIT exists, check if it exceeds default
		limitVal, ok := selectStmt.Limit.Rowcount.(*sqlparser.SQLVal)
		if !ok {
			return "", domain.ErrInvalidQuery
		}

		// Convert the limit value to integer
		val, err := strconv.Atoi(string(limitVal.Val))
		if err != nil {
			return "", domain.ErrInvalidQuery
		}

		if val > defaultLimit {
			// Replace with default limit
			selectStmt.Limit.Rowcount = sqlparser.NewIntVal([]byte(fmt.Sprintf("%d", defaultLimit)))
		}
	}

	// Convert back to string
	return sqlparser.String(stmt), nil
}

package pkg

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
)

// Common regular expressions for SQL parsing
var (
	selectRegex       = regexp.MustCompile(`(?i)^\s*SELECT\s+(.+?)(?:\s+FROM\s|$)`)
	fromRegex         = regexp.MustCompile(`(?i)\s+FROM\s+([^\s;]+)`)
	whereRegex        = regexp.MustCompile(`(?i)\s+WHERE\s+(.+?)(?:\s+(?:GROUP BY|ORDER BY|LIMIT|OFFSET|SAMPLE|$))`)
	orderByRegex      = regexp.MustCompile(`(?i)\s+ORDER\s+BY\s+(.+?)(?:\s+(?:LIMIT|OFFSET|SAMPLE|$))`)
	limitRegex        = regexp.MustCompile(`(?i)\s+LIMIT\s+(\d+)`)
	offsetRegex       = regexp.MustCompile(`(?i)\s+OFFSET\s+(\d+)`)
	sampleRegex       = regexp.MustCompile(`(?i)\s+SAMPLE\s+(\d+(?:\.\d+)?)(?:\s+|$)`)
	multipleStmtRegex = regexp.MustCompile(`;[\s\n\r]*[^;\s\n\r]+`)
)

type SQLStatement struct {
	Type     string   // SELECT, INSERT, etc.
	Columns  []string // Selected columns
	Table    string   // FROM table
	Where    string   // WHERE clause
	OrderBy  string   // ORDER BY clause
	Limit    *int     // LIMIT clause
	Offset   *int     // OFFSET clause
	Sample   *float64 // SAMPLE clause
	RawQuery string   // Original query string
}

// IsSelectStatement checks if the given query is a valid SELECT statement
func IsSelectStatement(query string) (bool, error) {
	query = strings.TrimSpace(query)
	if !strings.HasPrefix(strings.ToUpper(query), "SELECT") {
		return false, nil
	}

	// Try to parse as SELECT statement
	_, err := Parse(query)
	if err != nil {
		return false, err
	}

	return true, nil
}

// IsReadOnlyQuery checks if the given query is a read-only operation
// This includes SELECT, WITH (CTEs), DESCRIBE, and SUMMARIZE statements only
// Note: SHOW, EXPLAIN, and PRAGMA are explicitly NOT allowed for security
func IsReadOnlyQuery(query string) bool {
	query = strings.TrimSpace(strings.ToUpper(query))

	// List of allowed read-only statement prefixes
	// Each prefix should be followed by whitespace or specific characters
	readOnlyPrefixes := []string{
		"SELECT ",
		"SELECT\t",
		"SELECT\n",
		"SELECT(", // For SELECT(column) style
		"WITH ",
		"WITH\t",
		"WITH\n",
		"DESCRIBE ",
		"DESCRIBE\t",
		"DESCRIBE\n",
		"SUMMARIZE ", // DuckDB statistical summary
		"SUMMARIZE\t",
		"SUMMARIZE\n",
		"SUMMARIZE(", // For SUMMARIZE(SELECT ...) style
	}

	for _, prefix := range readOnlyPrefixes {
		if strings.HasPrefix(query, prefix) {
			return true
		}
	}

	// Special case for single word commands that might not have a space after
	if query == "DESCRIBE" || query == "SUMMARIZE" {
		return true
	}

	return false
}

// HasMultipleStatements checks if the query contains multiple SQL statements
func HasMultipleStatements(query string) (bool, error) {
	// Remove comments and normalize whitespace
	query = removeComments(query)
	query = strings.TrimSpace(query)

	// Look for semicolons followed by non-whitespace
	return multipleStmtRegex.MatchString(query), nil
}

// ImposeLimits adds or validates LIMIT clause
func ImposeLimits(query string, defaultLimit int) (string, error) {
	stmt, err := Parse(query)
	if err != nil {
		return "", err
	}

	// If no LIMIT exists or current LIMIT exceeds default
	if stmt.Limit == nil || *stmt.Limit > defaultLimit {
		newQuery := strings.TrimRight(query, ";")
		limitClause := fmt.Sprintf(" LIMIT %d", defaultLimit)

		// Remove existing LIMIT if present
		if stmt.Limit != nil {
			limIdx := strings.Index(strings.ToUpper(newQuery), "LIMIT")
			newQuery = newQuery[:limIdx]
		}

		return newQuery + limitClause, nil
	}

	return query, nil
}

// Parse parses a SQL query into a SQLStatement struct
func Parse(query string) (*SQLStatement, error) {
	query = removeComments(query)
	query = strings.TrimSpace(query)

	stmt := &SQLStatement{
		RawQuery: query,
		Type:     "SELECT", // We're only handling SELECT statements for now
	}

	// Parse SELECT clause
	selectMatch := selectRegex.FindStringSubmatch(query)
	if selectMatch == nil {
		return nil, fmt.Errorf("invalid SELECT statement")
	}
	stmt.Columns = parseColumns(selectMatch[1])

	// Parse FROM clause
	fromMatch := fromRegex.FindStringSubmatch(query)
	if fromMatch != nil {
		stmt.Table = fromMatch[1]
	}

	// Parse WHERE clause
	whereMatch := whereRegex.FindStringSubmatch(query)
	if whereMatch != nil {
		stmt.Where = strings.TrimSpace(whereMatch[1])
	}

	// Parse ORDER BY clause
	orderByMatch := orderByRegex.FindStringSubmatch(query)
	if orderByMatch != nil {
		stmt.OrderBy = strings.TrimSpace(orderByMatch[1])
	}

	// Parse LIMIT clause
	limitMatch := limitRegex.FindStringSubmatch(query)
	if limitMatch != nil {
		if limit, err := strconv.Atoi(limitMatch[1]); err == nil {
			stmt.Limit = &limit
		}
	}

	// Parse OFFSET clause
	offsetMatch := offsetRegex.FindStringSubmatch(query)
	if offsetMatch != nil {
		if offset, err := strconv.Atoi(offsetMatch[1]); err == nil {
			stmt.Offset = &offset
		}
	}

	// Parse SAMPLE clause
	sampleMatch := sampleRegex.FindStringSubmatch(query)
	if sampleMatch != nil {
		if sample, err := strconv.ParseFloat(sampleMatch[1], 64); err == nil {
			stmt.Sample = &sample
		}
	}

	return stmt, nil
}

// Helper functions

func parseColumns(columnsStr string) []string {
	columnsStr = strings.TrimSpace(columnsStr)
	if columnsStr == "*" {
		return []string{"*"}
	}

	var columns []string
	var currentCol strings.Builder
	depth := 0
	inQuote := false
	prevChar := ' '

	for _, char := range columnsStr {
		switch char {
		case '(':
			if !inQuote {
				depth++
			}
			currentCol.WriteRune(char)
		case ')':
			if !inQuote {
				depth--
			}
			currentCol.WriteRune(char)
		case '"', '\'':
			if prevChar != '\\' {
				inQuote = !inQuote
			}
			currentCol.WriteRune(char)
		case ',':
			if depth == 0 && !inQuote {
				columns = append(columns, strings.TrimSpace(currentCol.String()))
				currentCol.Reset()
			} else {
				currentCol.WriteRune(char)
			}
		default:
			currentCol.WriteRune(char)
		}
		prevChar = char
	}

	if currentCol.Len() > 0 {
		columns = append(columns, strings.TrimSpace(currentCol.String()))
	}

	return columns
}

func removeComments(query string) string {
	var result strings.Builder
	lines := strings.SplitSeq(query, "\n")

	for line := range lines {
		// Remove inline comments
		if idx := strings.Index(line, "--"); idx != -1 {
			line = line[:idx]
		}
		if len(strings.TrimSpace(line)) > 0 {
			result.WriteString(line + " ")
		}
	}

	// Remove multi-line comments
	queryStr := result.String()
	for {
		startIdx := strings.Index(queryStr, "/*")
		if startIdx == -1 {
			break
		}
		endIdx := strings.Index(queryStr[startIdx:], "*/")
		if endIdx == -1 {
			break
		}
		queryStr = queryStr[:startIdx] + " " + queryStr[startIdx+endIdx+2:]
	}

	return strings.TrimSpace(queryStr)
}

func escapeIdentifierPart(part string) string {
	trimmedPart := strings.TrimSpace(part)

	if trimmedPart == "*" {
		return trimmedPart
	}

	if strings.HasPrefix(trimmedPart, `"`) && strings.HasSuffix(trimmedPart, `"`) {
		return trimmedPart
	}

	return fmt.Sprintf(`"%s"`, trimmedPart)
}

func escapeColumn(col string) string {
	trimmedCol := strings.TrimSpace(col)

	if strings.Contains(strings.ToUpper(trimmedCol), " AS ") {
		asIndex := strings.Index(strings.ToUpper(trimmedCol), " AS ")
		if asIndex != -1 {
			beforeAs := trimmedCol[:asIndex]
			afterAs := trimmedCol[asIndex+4:] // len(" AS ") is 4
			return fmt.Sprintf("%s AS %s", escapeColumn(beforeAs), escapeIdentifierPart(afterAs))
		}
	}

	if strings.Contains(trimmedCol, "(") && strings.Contains(trimmedCol, ")") {
		return trimmedCol
	}

	parts := strings.Split(trimmedCol, ".")
	escapedParts := make([]string, len(parts))

	for i, part := range parts {
		escapedParts[i] = escapeIdentifierPart(part)
	}

	return strings.Join(escapedParts, ".")
}

func escapeColumns(columns []string) []string {
	escaped := make([]string, len(columns))
	for i, col := range columns {
		escaped[i] = escapeColumn(col)
	}
	return escaped
}

var filterKeyRegex = regexp.MustCompile(`^filter\[([^\]]+)\]([a-z]+)?$`)

// BuildSelectQueryFromRestParams converts REST parameters to a SQL query
func BuildSelectQueryFromRestParams(params models.RestParams) (string, error) {
	var queryParts []string

	// SELECT clause
	if len(params.Cols) > 0 {
		queryParts = append(queryParts, "SELECT "+strings.Join(escapeColumns(params.Cols), ", "))
	} else {
		queryParts = append(queryParts, "SELECT *")
	}

	// FROM clause
	queryParts = append(queryParts, "FROM "+params.Table)

	// WHERE clause
	if len(params.Filter) > 0 {
		whereClause, err := buildWhereClause(params.Filter)
		if err != nil {
			return "", err
		}
		if whereClause != "" {
			queryParts = append(queryParts, "WHERE "+whereClause)
		}
	}

	// ORDER BY clause
	if params.Sort != "" {
		orderBy, err := buildOrderByClause(params.Sort)
		if err != nil {
			return "", err
		}
		if orderBy != "" {
			queryParts = append(queryParts, "ORDER BY "+orderBy)
		}
	}

	// LIMIT and OFFSET
	if params.Limit != 0 {
		queryParts = append(queryParts, fmt.Sprintf("LIMIT %d", params.Limit))
		if params.Page > 1 {
			offset := (params.Page - 1) * params.Limit
			queryParts = append(queryParts, fmt.Sprintf("OFFSET %d", offset))
		}
	}

	return strings.Join(queryParts, " "), nil
}

// BuildCountQuery converts a SELECT query to a COUNT query
func BuildCountQuery(query string) (string, error) {
	stmt, err := Parse(query)
	if err != nil {
		return "", err
	}

	// Build count query
	var queryParts []string
	// Preserve quotes if they exist in the original table name
	tableName := stmt.Table
	if strings.HasPrefix(tableName, `"`) && strings.HasSuffix(tableName, `"`) {
		queryParts = append(queryParts, fmt.Sprintf(`SELECT COUNT(*) FROM %s`, tableName))
	} else {
		queryParts = append(queryParts, fmt.Sprintf(`SELECT COUNT(*) FROM "%s"`, tableName))
	}

	if stmt.Where != "" {
		queryParts = append(queryParts, "WHERE "+stmt.Where)
	}

	return strings.Join(queryParts, " "), nil
}

func buildWhereClause(filters map[string]string) (string, error) {
	var conditions []string

	for key, val := range filters {
		condition, err := parseFilter(key, val)
		if err != nil {
			return "", err
		}
		if condition != "" {
			conditions = append(conditions, condition)
		}
	}

	if len(conditions) == 0 {
		return "", nil
	}

	return strings.Join(conditions, " AND "), nil
}

func parseFilter(key, val string) (string, error) {
	matches := filterKeyRegex.FindStringSubmatch(key)
	if matches == nil {
		return "", nil
	}

	colName := matches[1]
	operator := strings.ReplaceAll(key, matches[0], "")

	if operator == "" {
		operator = "="
	} else {
		switch operator {
		case "lt":
			operator = "<"
		case "gt":
			operator = ">"
		case "lte":
			operator = "<="
		case "gte":
			operator = ">="
		default:
			return "", domain.ErrInvalidFilterOperator
		}
	}

	// Handle value
	var processedVal string
	if strings.HasPrefix(val, "'") && strings.HasSuffix(val, "'") {
		// String value
		processedVal = val
	} else {
		// Try to parse as number
		if _, err := strconv.ParseFloat(val, 64); err != nil {
			return "", domain.ErrInvalidFilterKey
		}
		processedVal = val
	}

	return fmt.Sprintf("%s %s %s", colName, operator, processedVal), nil
}

func buildOrderByClause(sort string) (string, error) {
	fields := strings.Split(sort, ",")
	var orderClauses []string

	for _, field := range fields {
		field = strings.TrimSpace(field)
		direction := "ASC"

		if strings.HasPrefix(field, "-") {
			direction = "DESC"
			field = strings.TrimPrefix(field, "-")
		}

		orderClauses = append(orderClauses, fmt.Sprintf("%s %s", field, direction))
	}

	return strings.Join(orderClauses, ", "), nil
}

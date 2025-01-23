package domain

type SqlError int

const (
	ErrMultipleSqlStatements SqlError = iota
	ErrNotSelectStatement
	ErrInvalidQuery
	ErrTableNotFound
)

// Error implements the error interface
func (e SqlError) Error() string {
	return e.String()
}

func (e SqlError) String() string {
	switch e {
	case ErrMultipleSqlStatements:
		return "multiple sql statements are not allowed"
	case ErrNotSelectStatement:
		return "only select statement is allowed"
	case ErrInvalidQuery:
		return "invalid query"
	case ErrTableNotFound:
		return "dataset not found"
	default:
		return "unknown error"
	}
}

// IsSqlError checks if an error is of type SqlError
func IsSqlError(err error) bool {
	_, ok := err.(SqlError)
	return ok
}

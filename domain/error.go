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

type RestParamsError int

const (
	ErrInvalidFilterKey RestParamsError = iota
	ErrInvalidFilterOperator
	ErrInvalidFilterValue
)

func (e RestParamsError) Error() string {
	return e.String()
}

func (e RestParamsError) String() string {
	switch e {
	case ErrInvalidFilterKey:
		return "invalid filter key"
	case ErrInvalidFilterOperator:
		return "invalid filter operator"
	case ErrInvalidFilterValue:
		return "invalid filter value"
	default:
		return "unknown error"
	}
}

func IsRestParamsError(err error) bool {
	_, ok := err.(RestParamsError)
	return ok

}

type AiError int

const (
	ErrFailedToGenerateSql AiError = iota
)

func (e AiError) Error() string {
	return e.String()
}

func (e AiError) String() string {
	switch e {
	case ErrFailedToGenerateSql:
		return "failed to generate sql"
	default:
		return "unknown error"
	}
}

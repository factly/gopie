package custom_errors

import "errors"

var (
	TableNotFound  = errors.New("table not found")
	NoObjectsFound = errors.New("no objects found in the given path")
	InvalidSQL     = errors.New("invalid sql query")
)

package duckdb

import (
	"database/sql"
	"database/sql/driver"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/mitchellh/mapstructure"
)

func rawConn(conn *sql.Conn, f func(driver.Conn) error) error {
	return conn.Raw(func(raw any) error {
		if c, ok := raw.(interface{ Raw() driver.Conn }); ok {
			raw = c.Raw()
		}
		driverConn, ok := raw.(driver.Conn)
		if !ok {
			return fmt.Errorf("internal: did not obtain a driver.Conn")
		}
		return f(driverConn)
	})
}

type sinkProperties struct {
	Table string `mapstructure:"table"`
}

func parseSinkProperties(props map[string]any) (*sinkProperties, error) {
	cfg := &sinkProperties{}
	if err := mapstructure.Decode(props, cfg); err != nil {
		return nil, fmt.Errorf("failed to parse sink properties: %w", err)
	}

	return cfg, nil
}

type dbSourceProperties struct {
	Database string `mapstructure:"db"`
	Sql      string `mapstructure:"sql"`
}

func parseDBSourceProperties(props map[string]any) (*dbSourceProperties, error) {
	cfg := &dbSourceProperties{}
	if err := mapstructure.Decode(props, cfg); err != nil {
		return nil, fmt.Errorf("failed to parse source properties: %w", err)
	}

	if cfg.Sql == "" {
		return nil, fmt.Errorf("property 'sql' is mandatory")
	}

	return cfg, nil
}

type fileSourceProperties struct {
	SQL                   string         `mapstructure:"sql"`
	DuckDB                map[string]any `mapstructure:"duckdb"`
	Format                string         `mapstructure:"format"`
	AllowSchemaRelaxation bool           `mapstructure:"allow_schema_relaxation"`
	BatchSize             string         `mapstructure:"batch_size"`
	CastToENUM            []string       `mapstructure:"cast_to_enum"`

	// Backwards compatibility
	HivePartitioning            *bool  `mapstructure:"hive_partitioning"`
	CSVDelimiter                string `mapstructure:"csvdelimiter"`
	IngestAllowSchemaRelaxation *bool  `mapstructure:"ingest.allow_schema_relaxation"`
}

func parseFileSourceProperties(props map[string]any) (*fileSourceProperties, error) {
	cfg := &fileSourceProperties{}
	if err := mapstructure.Decode(props, cfg); err != nil {
		return nil, fmt.Errorf("failed to parse source properties: %w", err)
	}

	if cfg.DuckDB == nil {
		cfg.DuckDB = map[string]any{}
	}

	if cfg.HivePartitioning != nil {
		cfg.DuckDB["hive_partitioning"] = *cfg.HivePartitioning
		cfg.HivePartitioning = nil
	}

	if cfg.CSVDelimiter != "" {
		cfg.DuckDB["delim"] = fmt.Sprintf("'%v'", cfg.CSVDelimiter)
		cfg.CSVDelimiter = ""
	}

	if cfg.IngestAllowSchemaRelaxation != nil {
		cfg.AllowSchemaRelaxation = *cfg.IngestAllowSchemaRelaxation
		cfg.IngestAllowSchemaRelaxation = nil
	}

	if cfg.AllowSchemaRelaxation {
		if val, ok := cfg.DuckDB["union_by_name"].(bool); ok && !val {
			return nil, fmt.Errorf("can't set 'union_by_name' and 'allow_schema_relaxation' at the same time")
		}

		if hasKey(cfg.DuckDB, "columns", "types", "dtypes") {
			return nil, fmt.Errorf("if any of 'columns', 'types', 'dtypes' is set allow_schema_relaxation must be disable")
		}
	}

	return cfg, nil
}

func sourceReader(paths []string, format string, ingestionProps map[string]any) (string, error) {
	if containsAny(format, []string{".csv", ".tsv", ".txt"}) {
		return generateReadCsvStatement(paths, ingestionProps)
	} else if containsAny(format, []string{".parquet"}) {
		return generateReadParquetStatement(paths, ingestionProps)
	} else if containsAny(format, []string{".json", ".ndjson"}) {
		return generateReadJSONStatement(paths, ingestionProps)
	}

	return "", fmt.Errorf("file type not supported: %s", format)
}

func generateReadCsvStatement(paths []string, properties map[string]any) (string, error) {
	ingestionProps := copyMap(properties)
	// set sample_size to 200000 by default
	if _, sampleSizeDefined := ingestionProps["sample_size"]; !sampleSizeDefined {
		ingestionProps["sample_size"] = 200000
	}
	// auto_detect (enables auto-detection of parameters) is true by default, it takes care of params/schema
	return fmt.Sprintf("read_csv_auto(%s)", convertToStatementParamsStr(paths, ingestionProps)), nil
}

func generateReadParquetStatement(paths []string, properties map[string]any) (string, error) {
	ingestionProps := copyMap(properties)
	// set hive_partitioning to true by default
	if _, hivePartitioningDefined := ingestionProps["hive_partitioning"]; !hivePartitioningDefined {
		ingestionProps["hive_partitioning"] = true
	}
	return fmt.Sprintf("read_parquet(%s)", convertToStatementParamsStr(paths, ingestionProps)), nil
}

func generateReadJSONStatement(paths []string, properties map[string]any) (string, error) {
	ingestionProps := copyMap(properties)
	// auto_detect is false by default so setting it to true simplifies the ingestion
	// if columns are defined then DuckDB turns the auto-detection off so no need to check this case here
	if _, autoDetectDefined := ingestionProps["auto_detect"]; !autoDetectDefined {
		ingestionProps["auto_detect"] = true
	}
	// set sample_size to 200000 by default
	if _, sampleSizeDefined := ingestionProps["sample_size"]; !sampleSizeDefined {
		ingestionProps["sample_size"] = 200000
	}
	// set format to auto by default
	if _, formatDefined := ingestionProps["format"]; !formatDefined {
		ingestionProps["format"] = "auto"
	}
	return fmt.Sprintf("read_json(%s)", convertToStatementParamsStr(paths, ingestionProps)), nil
}

func convertToStatementParamsStr(paths []string, properties map[string]any) string {
	ingestionParamsStr := make([]string, 0, len(properties)+1)
	// The first parameter is a source path
	ingestionParamsStr = append(ingestionParamsStr, fmt.Sprintf("['%s']", strings.Join(paths, "','")))
	for key, value := range properties {
		ingestionParamsStr = append(ingestionParamsStr, fmt.Sprintf("%s=%v", key, value))
	}
	return strings.Join(ingestionParamsStr, ",")
}

type duckDBTableSchemaResult struct {
	ColumnName string  `db:"column_name"`
	ColumnType string  `db:"column_type"`
	Nullable   *string `db:"nullable"`
	Key        *string `db:"key"`
	Default    *string `db:"default"`
	Extra      *string `db:"extra"`
}

// utility functions
func hasKey(m map[string]interface{}, key ...string) bool {
	for _, k := range key {
		if _, ok := m[k]; ok {
			return true
		}
	}
	return false
}

func missingMapKeys(src, lookup map[string]string) []string {
	keys := make([]string, 0)
	for k := range src {
		if _, ok := lookup[k]; !ok {
			keys = append(keys, k)
		}
	}
	return keys
}

func keys(src map[string]string) []string {
	keys := make([]string, 0, len(src))
	for k := range src {
		keys = append(keys, k)
	}
	return keys
}

func names(filePaths []string) []string {
	names := make([]string, len(filePaths))
	for i, f := range filePaths {
		names[i] = filepath.Base(f)
	}
	return names
}

// copyMap does a shallow copy of the map
func copyMap(originalMap map[string]any) map[string]any {
	newMap := make(map[string]any, len(originalMap))
	for key, value := range originalMap {
		newMap[key] = value
	}
	return newMap
}

func containsAny(s string, targets []string) bool {
	source := strings.ToLower(s)
	for _, target := range targets {
		if strings.Contains(source, target) {
			return true
		}
	}
	return false
}

func fileSize(paths []string) int64 {
	var size int64
	for _, path := range paths {
		if info, err := os.Stat(path); err == nil { // ignoring error since only error possible is *PathError
			size += info.Size()
		}
	}
	return size
}

func quoteName(name string) string {
	return fmt.Sprintf("\"%s\"", name)
}

func escapeDoubleQuotes(column string) string {
	return strings.ReplaceAll(column, "\"", "\"\"")
}

func safeName(name string) string {
	if name == "" {
		return name
	}
	return quoteName(escapeDoubleQuotes(name))
}

func RowsToSchema(r *sql.Rows) (*StructType, error) {
	if r == nil {
		return nil, nil
	}

	cts, err := r.ColumnTypes()
	if err != nil {
		return nil, err
	}

	fields := make([]*StructType_Field, len(cts))

	for i, ct := range cts {
		nullable, ok := ct.Nullable()
		if !ok {
			nullable = true
		}

		t, err := databaseTypeToJson(ct.DatabaseTypeName(), nullable)
		if err != nil {
			return nil, err
		}

		fields[i] = &StructType_Field{
			Name: ct.Name(),
			Type: t,
		}
	}
	return &StructType{fields}, nil
}

func databaseTypeToJson(dbt string, nullable bool) (*Type, error) {
	ty := &Type{Nullable: nullable}
	types := []string{
		"INVALID",
		"BOOLEAN",
		"TINYINT",
		"SMALLINT",
		"INTEGER",
		"BIGINT",
		"UTINYINT",
		"USMALLINT",
		"UINTEGER",
		"UBIGINT",
		"FLOAT",
		"DOUBLE",
		"TIMESTAMP",
		"TIMESTAMPTZ", "TIMESTAMP WITH TIME ZONE",
		"DATE",
		"TIME",
		"TIME WITH TIME ZONE",
		"INTERVAL",
		"HUGEINT",
		"VARCHAR",
		"BLOB",
		"TIMESTAMP_S",
		"TIMESTAMP_MS",
		"TIMESTAMP_NS",
		"ENUM",
		"UUID",
		"JSON",
		"CHAR",
		"NULL",
	}

	for _, t := range types {
		if t == dbt {
			ty.Code = dbt
			return ty, nil
		}
	}

	if strings.HasSuffix(dbt, "[]") {
		at, err := databaseTypeToJson(dbt[0:len(dbt)-2], true)
		if err != nil {
			return nil, err
		}
		ty.Code = "ARRAY_TYPE"
		ty.ArrayElementType = at
		return ty, nil
	}

	base, args, ok := splitBaseAndArgs(dbt)
	if !ok {
		return nil, fmt.Errorf("encountered unsupported duckdb type '%s'", dbt)
	}

	switch base {
	case "DECIMAL":
		ty.Code = base
	case "STRUCT":
		ty.Code = base

		ty.StructType = &StructType{}

		fieldStrs := splitCommasUnlessQuotedOrNestedInParens(args)
		for _, fieldStr := range fieldStrs {
			// Each field has format `name TYPE` or `"name" TYPE`
			fieldName, fieldTypeStr, ok := splitStructFieldStr(fieldStr)
			if !ok {
				return nil, fmt.Errorf("encountered unsupported duckdb type '%s'", dbt)
			}

			// Convert to type
			fieldType, err := databaseTypeToJson(fieldTypeStr, true)
			if err != nil {
				return nil, err
			}

			// Add to fields
			ty.StructType.Fields = append(ty.StructType.Fields, &StructType_Field{
				Name: fieldName,
				Type: fieldType,
			})
		}

	case "MAP":
		fieldStrs := splitCommasUnlessQuotedOrNestedInParens(args)
		if len(fieldStrs) != 2 {
			return nil, fmt.Errorf("encountered unsupported duckdb type '%s'", dbt)
		}

		keyType, err := databaseTypeToJson(fieldStrs[0], true)
		if err != nil {
			return nil, err
		}

		valType, err := databaseTypeToJson(fieldStrs[1], true)
		if err != nil {
			return nil, err
		}

		ty.Code = dbt
		ty.MapType = &MapType{
			KeyType:   keyType,
			ValueType: valType,
		}
	case "ENUM":
		ty.Code = dbt // representing enums as strings for now
	default:
		return nil, fmt.Errorf("encountered unsupported duckdb type '%s'", dbt)
	}
	return ty, nil
}

func splitBaseAndArgs(s string) (string, string, bool) {
	// Split on opening parenthesis
	base, rest, found := strings.Cut(s, "(")
	if !found {
		return "", "", false
	}

	// Remove closing parenthesis
	rest = rest[0 : len(rest)-1]

	return base, rest, true
}

func splitCommasUnlessQuotedOrNestedInParens(s string) []string {
	// Result slice
	splits := []string{}
	// Starting idx of current split
	fromIdx := 0
	// True if quote level is unmatched (this is sufficient for escaped quotes since they will immediately flip again)
	quoted := false
	// Nesting level
	nestCount := 0

	// Consume input character-by-character
	for idx, char := range s {
		// Toggle quoted
		if char == '"' {
			quoted = !quoted
			continue
		}
		// If quoted, don't parse for nesting or commas
		if quoted {
			continue
		}
		// Increase nesting on opening paren
		if char == '(' {
			nestCount++
			continue
		}
		// Decrease nesting on closing paren
		if char == ')' {
			nestCount--
			continue
		}
		// If nested, don't parse for commas
		if nestCount != 0 {
			continue
		}
		// If not nested and there's a comma, add split to result
		if char == ',' {
			splits = append(splits, s[fromIdx:idx])
			fromIdx = idx + 1
			continue
		}
		// If not nested, and there's a space at the start of the split, skip it
		if fromIdx == idx && char == ' ' {
			fromIdx++
			continue
		}
	}

	// Add last split to result and return
	splits = append(splits, s[fromIdx:])
	return splits
}

func splitStructFieldStr(fieldStr string) (string, string, bool) {
	// If the string DOES NOT start with a `"`, we can just split on the first space.
	if fieldStr == "" || fieldStr[0] != '"' {
		return strings.Cut(fieldStr, " ")
	}

	// Find end of quoted string (skipping `""` since they're escaped quotes)
	idx := 1
	found := false
	for !found && idx < len(fieldStr) {
		// Continue if not a quote
		if fieldStr[idx] != '"' {
			idx++
			continue
		}

		// Skip two ahead if it's two quotes in a row (i.e. an escaped quote)
		if len(fieldStr) > idx+1 && fieldStr[idx+1] == '"' {
			idx += 2
			continue
		}

		// It's the last quote of the string. We're done.
		idx++
		found = true
	}

	// If not found, format was unexpected
	if !found {
		return "", "", false
	}

	// Remove surrounding `"` and replace escaped quotes `""` with `"`
	nameStr := strings.ReplaceAll(fieldStr[1:idx-1], `""`, `"`)

	// The rest of the string is the type, minus the initial space
	typeStr := strings.TrimLeft(fieldStr[idx:], " ")

	return nameStr, typeStr, true
}

func dbName(name, version string) string {
	return fmt.Sprintf("%s_%s", name, version)
}

func removeDBFile(dbFile string) {
	_ = os.Remove(dbFile)
	// Hacky approach to remove the wal and tmp file
	_ = os.Remove(dbFile + ".wal")
	_ = os.RemoveAll(dbFile + ".tmp")
}

// safeSQLName returns a quoted SQL identifier.
func safeSQLName(name string) string {
	if name == "" {
		return name
	}
	return fmt.Sprintf("\"%s\"", strings.ReplaceAll(name, "\"", "\"\""))
}

func safeSQLString(name string) string {
	if name == "" {
		return name
	}
	return fmt.Sprintf("'%s'", strings.ReplaceAll(name, "'", "''"))
}

func MapScan(r ColScanner, dest map[string]any) error {
	// ignore r.started, since we needn't use reflect for anything.
	columns, err := r.Columns()
	if err != nil {
		return err
	}

	values := make([]interface{}, len(columns))
	for i := range values {
		values[i] = new(interface{})
	}

	err = r.Scan(values...)
	if err != nil {
		return err
	}

	for i, column := range columns {
		dest[column] = *(values[i].(*interface{}))
	}

	return r.Err()
}

package duckdb

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/XSAM/otelsql"
	"github.com/c2h5oh/datasize"
	"github.com/factly/gopie/pkg"
	"github.com/jmoiron/sqlx"
	"github.com/marcboeker/go-duckdb"
	"golang.org/x/sync/semaphore"
)

type Statement struct {
	Query            string
	Args             []any
	DryRun           bool
	Priority         int
	LongRunning      bool
	ExecutionTimeout time.Duration
}

type Type struct {
	Code             string      `json:"code"`
	Nullable         bool        `json:"nullable"`
	ArrayElementType *Type       `json:"array_element_type"`
	StructType       *StructType `json:"struct_type"`
	MapType          *MapType    `json:"map_type"`
}

type StructType struct {
	Fields []*StructType_Field `json:"fields"`
}

type StructType_Field struct {
	Name string `json:"name"`
	Type *Type  `json:"type"`
}

type MapType struct {
	KeyType   *Type `json:"key_type"`
	ValueType *Type `json:"value_type"`
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

type Result struct {
	*sql.Rows
	Schema    *StructType
	cleanupFn func() error
}

// SetCleanupFunc sets a function, which will be called when the Result is closed.
func (r *Result) SetCleanupFunc(fn func() error) {
	if r.cleanupFn != nil {
		panic("cleanup function already set")
	}
	r.cleanupFn = fn
}

// Close wraps rows.Close and calls the Result's cleanup function (if it is set).
// Close should be idempotent.
func (r *Result) Close() error {
	firstErr := r.Rows.Close()
	if r.cleanupFn != nil {
		err := r.cleanupFn()
		if firstErr == nil {
			firstErr = err
		}

		// Prevent cleanupFn from being called multiple times.
		// NOTE: Not idempotent for error returned from cleanupFn.
		r.cleanupFn = nil
	}
	return firstErr
}

type Driver struct {
	name string
}

func (d Driver) Open(cfgMap map[string]any, logger pkg.Logger) (*Connection, error) {
	cfg, err := newConfig(cfgMap)
	if err != nil {
		return nil, err
	}
	logger.Info("opening duckdb handle...")

	if cfg.DBFilePath != "" {
		tmpPath := cfg.DBFilePath + ".tmp"
		_ = os.RemoveAll(tmpPath)

		walPath := cfg.DBFilePath + ".wal"
		if stat, err := os.Stat(walPath); err == nil {
			if stat.Size() >= 100*int64(datasize.MB) {
				_ = os.Remove(walPath)
			}
		}
	}

	if cfg.DBStoragePath != "" {
		if err := os.MkdirAll(cfg.DBStoragePath, fs.ModePerm); err != nil && !errors.Is(err, fs.ErrExist) {
			return nil, err
		}
	}

	olapSemSize := cfg.PoolSize - 1
	if olapSemSize < 1 {
		olapSemSize = 1
	}

	ctx, cancel := context.WithCancel(context.Background())

	c := &Connection{
		config:         cfg,
		ctx:            ctx,
		cancel:         cancel,
		logger:         &logger,
		metaSem:        semaphore.NewWeighted(1),
		longRunningSem: semaphore.NewWeighted(1),
		dbCond:         sync.NewCond(&sync.Mutex{}),
		driverConfig:   cfgMap,
		driverName:     d.name,
		connTimes:      make(map[int]time.Time),
	}

	err = c.reopenDB()
	if err != nil {
		if c.config.ErrorOnIncompatibleVersion || !strings.Contains(err.Error(), "created with an older, incompatible version of Gopie ") {
			return nil, err
		}

		c.logger.Logger.Debug("Resetting .db file because it was created with an older, incompatible version of rill")

		tmpPath := cfg.DBFilePath + ".tmp"
		_ = os.RemoveAll(tmpPath)
		walPath := cfg.DBFilePath + ".wal"
		_ = os.Remove(walPath)
		_ = os.Remove(cfg.DBFilePath)

		if err := c.reopenDB(); err != nil {
			return nil, err
		}
	}

	conn, err := c.db.Connx(context.Background())
	if err != nil && strings.Contains(err.Error(), "Symbol is not found") {
		fmt.Printf("Your version of macOs is not supported.")
		os.Exit(1)
	} else if err == nil {
		conn.Close()
	} else {
		return nil, err
	}

	return c, nil
}

type Connection struct {
	db             *sqlx.DB
	driverConfig   map[string]any
	driverName     string
	config         *config
	logger         *pkg.Logger
	metaSem        *semaphore.Weighted
	longRunningSem *semaphore.Weighted
	txMu           sync.RWMutex
	dbConnCount    int
	dbCond         *sync.Cond
	dbReopen       bool
	dbErr          error
	connTimesMu    sync.Mutex
	nextConnID     int
	connTimes      map[int]time.Time
	ctx            context.Context
	cancel         context.CancelFunc
}

func (c *Connection) Driver() string {
	return c.driverName
}

func (c *Connection) Config() map[string]any {
	return c.driverConfig
}

func (c *Connection) Close() error {
	c.cancel()
	return c.db.Close()
}

func (c *Connection) reopenDB() error {
	if c.db != nil {
		err := c.db.Close()
		if err != nil {
			return err
		}
		c.db = nil
	}

	var bootQueries []string

	if c.config.BootQueries != "" {
		bootQueries = append(bootQueries, c.config.BootQueries)
	}

	bootQueries = append(bootQueries,
		"INSTALL 'json'",
		"LOAD 'json'",
		"INSTALL 'icu'",
		"LOAD 'icu'",
		"INSTALL 'parquet'",
		"LOAD 'parquet'",
		"INSTALL 'httpfs'",
		"LOAD 'httpfs'",
		"INSTALL 'sqlite'",
		"LOAD 'sqlite'",
		"SET max_expression_depth TO 250",
		"SET timezone='UTC'",
		"SET old_implicit_casting = true", // Implicit Cast to VARCHAR
	)

	if !c.config.AllowHostAccess {
		bootQueries = append(bootQueries, "SET preserve_insertion_order TO false")
	}

	connector, err := duckdb.NewConnector(c.config.DSN, func(execer driver.ExecerContext) error {
		for _, qry := range bootQueries {
			_, err := execer.ExecContext(context.Background(), qry, nil)
			if err != nil && strings.Contains(err.Error(), "Failed to download extension") {
				_, err = execer.ExecContext(context.Background(), qry+"FROM 'http://nightly-extensions.duckdb.org'", nil)
			}

			if err != nil {
				return err
			}
		}
		return nil
	})

	if err != nil {
		if strings.Contains(err.Error(), "Trying to read a database file with version number") {
			return fmt.Errorf("database file %q was created with an older, incompatible verison of Gopie (please remove it and try again)", c.config.DSN)
		}

		if strings.Contains(err.Error(), "Could not set lock on file") {
			return fmt.Errorf("failed to open database (is gopie already running?): %w", err)
		}

		return err
	}

	sqlDB := otelsql.OpenDB(connector)
	db := sqlx.NewDb(sqlDB, "duckdb")
	db.SetMaxOpenConns(c.config.PoolSize)
	c.db = db

	if !c.config.ExtTableStorage {
		return nil
	}

	conn, err := db.Connx(context.Background())

	if err != nil {
		return nil
	}

	defer conn.Close()

	_, err = conn.ExecContext(context.Background(), `
		select
			coalesce(t.table_catalog, current_database()) as "database",
			t.table_schema as "schema",
			t.table_name as "name",
			t.table_type as "type", 
			array_agg(c.column_name order by c.ordinal_position) as "column_names",
			array_agg(c.data_type order by c.ordinal_position) as "column_types",
			array_agg(c.is_nullable = 'YES' order by c.ordinal_position) as "column_nullable"
		from information_schema.tables t
		join information_schema.columns c on t.table_schema = c.table_schema and t.table_name = c.table_name
		group by 1, 2, 3, 4
		order by 1, 2, 3, 4
	`)
	if err != nil {
		return err
	}

	entries, err := os.ReadDir(c.config.DBStoragePath)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		path := filepath.Join(c.config.DBStoragePath, entry.Name())
		version, exist, err := c.tableVersion(entry.Name())

		if err != nil {
			c.logger.Error("error in fetching db verison: ", err.Error())
			_ = os.RemoveAll(path)
			continue
		}
		if !exist {
			_ = os.RemoveAll(path)
			continue
		}

		dbFile := filepath.Join(path, fmt.Sprintf("%s.db", version))
		db := dbName(entry.Name(), version)
		_, err = conn.ExecContext(context.Background(), fmt.Sprintf("ATTACH %s AS %s", safeSQLString(dbFile), safeSQLName(db)))

		if err != nil {
			c.logger.Error("attach failed clearing db file", err.Error())
			_, _ = conn.ExecContext(context.Background(), fmt.Sprintf("DROP VIEW IF EXISTS %s", safeSQLName(entry.Name())))
			_ = os.RemoveAll(path)
		}
	}

	return nil
}

// acquireMetaConn gets a connection from the pool for "meta" queries like catalog and information schema (i.e. fast queries).
// It returns a function that puts the connection back in the pool (if applicable).
func (c *Connection) acquireMetaConn(ctx context.Context) (*sqlx.Conn, func() error, error) {
	// Try to get conn from context (means the call is wrapped in WithConnection)
	conn := connFromContext(ctx)
	if conn != nil {
		return conn, func() error { return nil }, nil
	}

	// Acquire semaphore
	err := c.metaSem.Acquire(ctx, 1)
	if err != nil {
		return nil, nil, err
	}

	// Get new conn
	conn, releaseConn, err := c.acquireConn(ctx, false)
	if err != nil {
		c.metaSem.Release(1)
		return nil, nil, err
	}

	// Build release func
	release := func() error {
		err := releaseConn()
		c.metaSem.Release(1)
		return err
	}

	return conn, release, nil
}

// checkErr marks the DB for reopening if the error is an internal DuckDB error.
// In all other cases, it just proxies the err.
// It should be wrapped around errors returned from DuckDB queries. **It must be called while still holding an acquired DuckDB connection.**
func (c *Connection) checkErr(err error) error {
	if err != nil {
		if strings.HasPrefix(err.Error(), "INTERNAL Error:") || strings.HasPrefix(err.Error(), "FATAL Error") {
			c.dbCond.L.Lock()
			defer c.dbCond.L.Unlock()
			c.dbReopen = true
			c.logger.Error("encountered internal DuckDB error - scheduling reopen of DuckDB", err.Error())
		}
	}
	return err
}

func (c *Connection) tableVersion(name string) (string, bool, error) {
	pathToFile := filepath.Join(c.config.DBStoragePath, name, "version.txt")
	contents, err := os.ReadFile(pathToFile)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			return "", false, nil
		}
		return "", false, err
	}
	return strings.TrimSpace(string(contents)), true, nil
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

func (c *Connection) accquireOLAPConn(ctx context.Context, longRunning, tx bool) (*sqlx.Conn, func() error, error) {
	conn := connFromContext(ctx)
	if conn != nil {
		return conn, func() error { return nil }, nil
	}

	if longRunning {
		err := c.longRunningSem.Acquire(ctx, 1)
		if err != nil {
			return nil, nil, err
		}
	}

	conn, releaseConn, err := c.acquireConn(ctx, tx)
	if err != nil {
		if longRunning {
			c.longRunningSem.Release(1)
		}
		return nil, nil, err
	}

	release := func() error {
		err := releaseConn()
		if longRunning {
			c.longRunningSem.Release(1)
		}
		return err
	}
	return conn, release, nil
}

// acquireConn returns a DuckDB connection. It should only be used internally in acquireMetaConn and acquireOLAPConn.
// acquireConn implements the connection tracking and DB reopening logic described in the struct definition for connection.
func (c *Connection) acquireConn(ctx context.Context, tx bool) (*sqlx.Conn, func() error, error) {
	c.dbCond.L.Lock()
	for {
		if c.dbErr != nil {
			c.dbCond.L.Unlock()
			return nil, nil, c.dbErr
		}
		if !c.dbReopen {
			break
		}
		c.dbCond.Wait()
	}

	c.dbConnCount++
	c.dbCond.L.Unlock()

	// Poor man's transaction support – see struct docstring for details.
	if tx {
		c.txMu.Lock()

		// When tx is true, and the database is backed by a file, we reopen the database to ensure only one DuckDB connection is open.
		// This avoids the following issue: https://github.com/duckdb/duckdb/issues/9150
		if c.config.DBFilePath != "" {
			err := c.reopenDB()
			if err != nil {
				c.txMu.Unlock()
				return nil, nil, err
			}
		}
	} else {
		c.txMu.RLock()
	}
	releaseTx := func() {
		if tx {
			c.txMu.Unlock()
		} else {
			c.txMu.RUnlock()
		}
	}

	conn, err := c.db.Connx(ctx)
	if err != nil {
		releaseTx()
		return nil, nil, err
	}

	c.connTimesMu.Lock()
	connID := c.nextConnID
	c.nextConnID++
	c.connTimes[connID] = time.Now()
	c.connTimesMu.Unlock()

	release := func() error {
		err := conn.Close()
		c.connTimesMu.Lock()
		delete(c.connTimes, connID)
		c.connTimesMu.Unlock()
		releaseTx()
		c.dbCond.L.Lock()
		c.dbConnCount--
		if c.dbConnCount == 0 && c.dbReopen {
			c.dbReopen = false
			err = c.reopenDB()
			if err == nil {
				c.logger.Info("reopened DuckDB successfully")
			} else {
				c.logger.Info("reopen of DuckDB failed - the handle is now permanently locked", err.Error())
			}
			c.dbErr = err
			c.dbCond.Broadcast()
		}
		c.dbCond.L.Unlock()
		return err
	}

	return conn, release, nil
}

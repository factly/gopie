package duckdb

import (
	"context"
	"errors"
	"fmt"
	"io"
	"strings"
	"time"

	"github.com/factly/gopie/pkg"
	"github.com/factly/gopie/pkg/duckdbsql"
	"github.com/factly/gopie/source"
)

type objectStoreToDuckDB struct {
	conn              *Connection
	objectStore       source.ObjectStore
	logger            *pkg.Logger
	objectStoreConfig map[string]any
}

func NewObjectStoreToDuckDB(conn *Connection, logger *pkg.Logger, objectStore source.ObjectStore) Transpoter {
	return &objectStoreToDuckDB{
		objectStore: objectStore,
		logger:      logger,
		conn:        conn,
	}
}

func (o *objectStoreToDuckDB) Transfer(ctx context.Context, srcProps, sinkProps map[string]any) error {
	sinkCfg, err := parseSinkProperties(sinkProps)
	if err != nil {
		return err
	}
	srcCfg, err := parseFileSourceProperties(srcProps)
	if err != nil {
		return err
	}

	iterator, err := o.objectStore.DownloadFiles(ctx, srcProps)
	if err != nil {
		return err
	}
	defer iterator.Close()

	if srcCfg.SQL != "" {
		return o.ingestDuckDBSQL(ctx, srcCfg.SQL, iterator, srcCfg, sinkCfg)
	}
	var format string
	appendToTable := false
	if srcCfg.Format != "" {
		format = fmt.Sprintf(".%s", srcCfg.Format)
	}

	if srcCfg.AllowSchemaRelaxation {
		srcCfg.DuckDB["union_by_name"] = true
	}

	a := newAppender(o.conn, sinkCfg, srcCfg.AllowSchemaRelaxation, o.logger, func(files []string) (string, error) {
		from, err := sourceReader(files, format, srcCfg.DuckDB)
		if err != nil {
			return "", err
		}
		return fmt.Sprintf("SELECT * FROM %s", from), nil
	})

	for {

		files, err := iterator.Next()
		if err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			return err
		}
		if format == "" {
			format = FullExt(files[0])
		}
		st := time.Now()
		o.logger.Info(fmt.Sprintf("ingesting files %s", files))

		if appendToTable {
			if err := a.appendData(ctx, files); err != nil {
				return err
			}
		} else {
			from, err := sourceReader(files, format, srcCfg.DuckDB)
			if err != nil {
				return err
			}

			err = o.conn.CreateTableAsSelect(ctx, sinkCfg.Table, fmt.Sprintf("SELECT * FROM %s", from))
			if err != nil {
				return err
			}
		}
		size := fileSize(files)
		o.logger.Info(fmt.Sprintf("ingested files %s, bytes_ingested: %d, duration: %d ms", files, size, time.Since(st).Milliseconds()))
		appendToTable = true
	}
	return nil
}

func (o *objectStoreToDuckDB) ingestDuckDBSQL(ctx context.Context, originalSQL string, iterator source.FileIterator, srcCfg *fileSourceProperties, dbSink *sinkProperties) error {
	ast, err := duckdbsql.Parse(originalSQL)
	if err != nil {
		o.logger.Error(err.Error())
		return err
	}

	refs := ast.GetTableRefs()
	if len(refs) != 1 {
		err := errors.New("sql source should have exacttly one table reference")
		o.logger.Error(err.Error())
		return err
	}
	ref := refs[0]

	if len(ref.Paths) == 0 {
		err := errors.New("only read_* functions with a single path is supported")
		o.logger.Error(err.Error())
		return err
	}
	if len(ref.Paths) > 1 {
		err := errors.New("invalid source, only a single path for source is supported")
		o.logger.Error(err.Error())
		return err
	}

	a := newAppender(o.conn, dbSink, srcCfg.AllowSchemaRelaxation, o.logger, func(files []string) (string, error) {
		return rewriteSQL(ast, files)
	})
	appendToTable := false
	for {
		files, err := iterator.Next()
		if err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			return err
		}

		st := time.Now()
		o.logger.Info(fmt.Sprintf("ingesting files %s ", files))
		if appendToTable {
			if err := a.appendData(ctx, files); err != nil {
				return err
			}
		} else {
			sql, err := rewriteSQL(ast, files)
			if err != nil {
				o.logger.Error(err.Error())
				return err
			}

			err = o.conn.CreateTableAsSelect(ctx, dbSink.Table, sql)
			if err != nil {
				return err
			}
		}

		size := fileSize(files)
		o.logger.Info(fmt.Sprintf("ingested files %s, bytes_ingested: %d, duration: %s", files, size, time.Since(st)))
		appendToTable = true
	}
	// TODO
	// if len(srcCfg.CastToENUM) > 0 {
	// }
	return nil
}

type appender struct {
	allowSchemaRelaxation bool
	tableSchema           map[string]string
	logger                *pkg.Logger
	sqlFunc               func([]string) (string, error)
	sink                  *sinkProperties
	conn                  *Connection
}

func newAppender(conn *Connection, sink *sinkProperties, allowSchemaRelaxation bool, logger *pkg.Logger, sqlFunc func([]string) (string, error)) *appender {
	return &appender{
		conn:                  conn,
		sink:                  sink,
		allowSchemaRelaxation: allowSchemaRelaxation,
		tableSchema:           nil,
		logger:                logger,
		sqlFunc:               sqlFunc,
	}
}

func (a *appender) appendData(ctx context.Context, files []string) error {
	sql, err := a.sqlFunc(files)
	if err != nil {
		a.logger.Error(err.Error())
		return err
	}

	err = a.conn.InsertTableAsSelect(ctx, a.sink.Table, a.allowSchemaRelaxation, sql)
	if err == nil || !a.allowSchemaRelaxation || containsAny(err.Error(), []string{"binder error", "conversion error"}) {
		return err
	}

	err = a.updateSchema(ctx, sql, files)
	if err != nil {
		return fmt.Errorf("failed to update schema %w", err)
	}

	return a.conn.InsertTableAsSelect(ctx, a.sink.Table, true, sql)
}

func (a *appender) scanSchemaFromQuery(ctx context.Context, qry string) (map[string]string, error) {
	result, err := a.conn.Execute(ctx, &Statement{Query: qry})

	schema := result.Schema
	s := make(map[string]string)

	for _, field := range schema.Fields {
		s[field.Name] = s[field.Type.Code]
	}

	return s, err
}

func (a *appender) updateSchema(ctx context.Context, sql string, fileNames []string) error {
	srcSchema, err := a.scanSchemaFromQuery(ctx, fmt.Sprintf("DESCRIBE (%s)", sql))
	if err != nil {
		return err
	}

	qry := fmt.Sprintf("DESCRIBE ((SELECT * FROM %s LIMIT 0) UNION ALL BY NAME (%s));", safeName(a.sink.Table), sql)
	unionSchema, err := a.scanSchemaFromQuery(ctx, qry)
	if err != nil {
		return err
	}

	if a.tableSchema == nil {
		a.tableSchema, err = a.scanSchemaFromQuery(ctx, fmt.Sprintf("DESCRIBE %s;", safeName(a.sink.Table)))
		if err != nil {
			a.logger.Error(err.Error())
			return err
		}
	}

	newCols := make(map[string]string)
	colTypeChanged := make(map[string]string)
	for colName, colType := range unionSchema {
		oldType, ok := a.tableSchema[colName]
		if !ok {
			newCols[colName] = colType
		} else if oldType != colType {
			colTypeChanged[colName] = colType
		}
	}

	if !a.allowSchemaRelaxation {
		if len(srcSchema) < len(unionSchema) {
			fileNames := strings.Join(names(fileNames), ",")
			columns := strings.Join(missingMapKeys(a.tableSchema, srcSchema), ",")
			return fmt.Errorf("new files %q are missing columns %q and schema relaxation not allowed", fileNames, columns)
		}

		if len(colTypeChanged) != 0 {
			fileNames := strings.Join(names(fileNames), ",")
			columns := strings.Join(keys(colTypeChanged), ",")
			return fmt.Errorf("new files %q change datatypes of some columns %q and schema relaxation not allowed", fileNames, columns)
		}
	}

	if len(newCols) != 0 && !a.allowSchemaRelaxation {
		fileNames := strings.Join(names(fileNames), ",")
		columns := strings.Join(missingMapKeys(srcSchema, a.tableSchema), ",")
		return fmt.Errorf("new files %q have new columns %q and schema relaxation not allowed", fileNames, columns)
	}

	for colName, colType := range newCols {
		a.tableSchema[colName] = colType
		if err := a.conn.AddTableColumn(ctx, a.sink.Table, colName, colType); err != nil {
			return err
		}
	}

	for colName, colType := range colTypeChanged {
		a.tableSchema[colName] = colType
		if err := a.conn.AlterTableColumn(ctx, a.sink.Table, colName, colType); err != nil {
			return err
		}
	}
	return nil
}

func rewriteSQL(ast *duckdbsql.AST, allFiles []string) (string, error) {
	err := ast.RewriteTableRefs(func(table *duckdbsql.TableRef) (*duckdbsql.TableRef, bool) {
		return &duckdbsql.TableRef{
			Paths:      allFiles,
			Function:   table.Function,
			Properties: table.Properties,
			Params:     table.Params,
		}, true
	})
	if err != nil {
		return "", err
	}
	sql, err := ast.Format()
	if err != nil {
		return "", err
	}
	return sql, nil
}

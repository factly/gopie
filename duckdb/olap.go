package duckdb

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/google/uuid"
)

type WithConnectionFunc func(wrappedCtx context.Context, ensuredCtx context.Context, conn *sql.Conn) error

func (c *Connection) WithConnection(ctx context.Context, longRunning, tx bool, fn WithConnectionFunc) error {
	if connFromContext(ctx) != nil {
		panic("nested withConnection")
	}

	conn, release, err := c.accquireOLAPConn(ctx, longRunning, tx)
	if err != nil {
		return err
	}
	defer func() { _ = release() }()

	wrappedCtx := contextWithConn(ctx, conn)
	ensuredCtx := contextWithConn(context.Background(), conn)
	return fn(wrappedCtx, ensuredCtx, conn.Conn)
}

func (c *Connection) Execute(ctx context.Context, stmt *Statement) (res *Result, outErr error) {
	if c.config.LogQueries {
		c.logger.Info("duckdb query: %v, %v", stmt.Query, stmt.Args)
	}

	if stmt.DryRun {
		conn, release, err := c.acquireMetaConn(ctx)
		if err != nil {
			return nil, err
		}
		defer func() { _ = release() }()

		name := uuid.NewString()

		_, err = conn.ExecContext(context.Background(), fmt.Sprintf("DROP VIEW %q", name))
		return nil, c.checkErr(err)
	}

	conn, release, err := c.accquireOLAPConn(ctx, stmt.LongRunning, false)
	if err != nil {
		return nil, err
	}

	var cancelFunc context.CancelFunc
	if stmt.ExecutionTimeout != 0 {
		ctx, cancelFunc = context.WithTimeout(ctx, stmt.ExecutionTimeout)
	}

	rows, err := conn.QueryContext(ctx, stmt.Query, stmt.Args...)
	if err != nil {
		if cancelFunc != nil {
			cancelFunc()
		}

		err = c.checkErr(err)
		_ = release()
		return nil, err
	}

	schema, err := RowsToSchema(rows)
	if err != nil {
		if cancelFunc != nil {
			cancelFunc()
		}

		err = c.checkErr(err)
		_ = release()
		return nil, err
	}
	res = &Result{
		Rows:   rows,
		Schema: schema,
	}

	res.SetCleanupFunc(func() error {
		if cancelFunc != nil {
			cancelFunc()
		}
		return release()
	})

	return res, nil
}

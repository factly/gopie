package api

import (
	"context"
	"fmt"
	"net/http"
	"strings"

	"github.com/factly/gopie/custom_errors"
	"github.com/factly/gopie/duckdb"
	"github.com/factly/x/errorx"
)

func imposeLimits(query string) string {
	if !strings.Contains(strings.ToLower(query), "limit") {
		strings.Replace(query, ";", "", 1)
		query = fmt.Sprintf("%s limit 1000", query)
	}
	return query
}

func (h *httpHandler) executeQuery(query, table string) (*duckdb.Result, error) {
	res, err := h.conn.Execute(context.Background(), &duckdb.Statement{Query: query})
	if err == custom_errors.TableNotFound {
		h.logger.Info("attaching table... ", "table", table)
		if err := h.conn.AttachOldTable(context.Background(), table); err != nil {
			return nil, err
		}

		return h.conn.Execute(context.Background(), &duckdb.Statement{Query: query})
	}
	return res, nil
}

func (h *httpHandler) handleError(w http.ResponseWriter, err error, logMessage string, defatulStatus int) {
	h.logger.Error(logMessage, "error", err.Error())
	status := defatulStatus
	message := err.Error()
	switch err {
	case custom_errors.TableNotFound:
		status = http.StatusNotFound
	case custom_errors.InvalidSQL:
		status = http.StatusBadRequest
	}

	errorx.Render(w, errorx.Parser(errorx.GetMessage(message, status)))
}

package api

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/factly/gopie/duckdb"
	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
	"github.com/xwb1989/sqlparser"
)

type sqlRequestBody struct {
	Query string `json:"query"`
}

func (h *httpHandler) sql(w http.ResponseWriter, r *http.Request) {
	var body sqlRequestBody

	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}
	defer r.Body.Close()

	err = validateQuery(body.Query)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusBadRequest)))
		return
	}

	res, err := h.conn.Execute(context.Background(), &duckdb.Statement{Query: body.Query})

	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	jsonRes, err := res.RowsToMap()
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	renderx.JSON(w, http.StatusOK, jsonRes)
}

func validateQuery(q string) error {
	stmt, err := sqlparser.Parse(q)
	if err != nil {
		return nil
	}

	switch stmt.(type) {
	case *sqlparser.Select:
		return nil
	default:
		return fmt.Errorf("Query is not read-only")
	}
}

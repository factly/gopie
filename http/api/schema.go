package api

import (
	"context"
	"fmt"
	"net/http"

	"github.com/factly/gopie/duckdb"
	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
	"github.com/go-chi/chi/v5"
)

func (h httpHandler) schema(w http.ResponseWriter, r *http.Request) {
	table := chi.URLParam(r, "tableName")

	res, err := h.conn.Execute(context.Background(), &duckdb.Statement{Query: fmt.Sprintf("desc %s", table)})
	if err != nil {
		fmt.Println(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	jsonRes, err := res.RowsToMap()
	if err != nil {
		fmt.Println(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	renderx.JSON(w, http.StatusOK, jsonRes)
}

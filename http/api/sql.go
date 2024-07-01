package api

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/factly/gopie/custom_errors"
	"github.com/factly/gopie/duckdb"
	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
)

type sqlRequestBody struct {
	Query string `json:"query"`
}

func (h *httpHandler) sql(w http.ResponseWriter, r *http.Request) {
	var body sqlRequestBody

	defer r.Body.Close()
	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}

	query := imposeLimits(body.Query)

	res, err := h.conn.Execute(context.Background(), &duckdb.Statement{Query: query})

	if err != nil {
		h.logger.Error(err.Error())
		if err == custom_errors.TableNotFound {
			errorx.Render(w, errorx.Parser(errorx.GetMessage("Table with given name is not found", http.StatusNotFound)))
			return
		} else if err == custom_errors.InvalidSQL {
			errorx.Render(w, errorx.Parser(errorx.GetMessage(fmt.Sprintf("invalid sql query: %s", body.Query), http.StatusBadRequest)))
			return
		}
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

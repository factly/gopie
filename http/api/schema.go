package api

import (
	"fmt"
	"net/http"

	"github.com/factly/gopie/custom_errors"
	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
	"github.com/go-chi/chi/v5"
)

func (h httpHandler) schema(w http.ResponseWriter, r *http.Request) {
	table := chi.URLParam(r, "tableName")

	jsonRes, err := getSchemaAsJson(h.conn, table)
	if err != nil {
		h.logger.Error(err.Error())
		if err == custom_errors.TableNotFound {
			errorx.Render(w, errorx.Parser(errorx.GetMessage(fmt.Sprintf("Table with name %s is not found", table), http.StatusNotFound)))
			return
		}
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	renderx.JSON(w, http.StatusOK, jsonRes)
}

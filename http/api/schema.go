package api

import (
	"fmt"
	"net/http"

	"github.com/factly/x/renderx"
	"github.com/go-chi/chi/v5"
)

func (h httpHandler) schema(w http.ResponseWriter, r *http.Request) {
	table := chi.URLParam(r, "tableName")

	res, err := h.executeQuery(fmt.Sprintf("DESC %s", table), table)
	if err != nil {
		h.handleError(w, err, "error executing schema query", http.StatusInternalServerError)
		return
	}

	jsonRes, err := res.RowsToMap()
	if err != nil {
		h.handleError(w, err, "error converting resutl to JSON", http.StatusInternalServerError)
		return
	}

	renderx.JSON(w, http.StatusOK, jsonRes)
}

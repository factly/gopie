package api

import (
	"fmt"
	"net/http"

	"github.com/factly/gopie/http/middleware"
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

	subject, ok := middleware.GetSubjectFromContext(r.Context())
	if ok {
		params := ingestEventParams{
			subject:        subject,
			dataset:        table,
			userID:         r.Header.Get("x-gopie-user-id"),
			organisationID: r.Header.Get("x-gopie-organisation-id"),
			method:         r.Method,
			endpoint:       r.URL.String(),
		}
		ingestEvent(h.metering, params)
	} else {
		h.logger.Error("Failed retriev subject")
	}

	renderx.JSON(w, http.StatusOK, jsonRes)
}

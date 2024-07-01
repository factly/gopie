package s3

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/factly/gopie/custom_errors"
	"github.com/factly/gopie/duckdb"
	"github.com/factly/gopie/pkg"
	"github.com/factly/x/errorx"
	"github.com/factly/x/renderx"
	"github.com/go-chi/chi/v5"
)

type httpHandler struct {
	logger      *pkg.Logger
	objectStore duckdb.Transpoter
}

func RegisterRoutes(router *chi.Mux, logger *pkg.Logger, objectStore duckdb.Transpoter) {
	handler := httpHandler{logger, objectStore}
	router.Mount("/source", handler.routes())
}

func (h *httpHandler) routes() chi.Router {
	router := chi.NewRouter()
	router.Post("/s3", h.upload)
	return router
}

type body struct {
	Path string `json:"path"`
}

func (h *httpHandler) upload(w http.ResponseWriter, r *http.Request) {
	var body body

	err := json.NewDecoder(r.Body).Decode(&body)
	if err != nil {
		h.logger.Error(err.Error())
		errorx.Render(w, errorx.Parser(errorx.GetMessage("Invalid request body", http.StatusBadRequest)))
		return
	}

	tableName := fmt.Sprintf("gp_%s", pkg.RandomString(12))

	err = h.objectStore.Transfer(context.Background(), map[string]any{
		"allow_schema_relaxation": false,
		"path":                    body.Path,
	},
		map[string]any{"table": tableName},
	)

	if err != nil {
		h.logger.Error(err.Error())
		if err == custom_errors.NoObjectsFound {
			errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusBadRequest)))
			return
		}
		errorx.Render(w, errorx.Parser(errorx.GetMessage(err.Error(), http.StatusInternalServerError)))
		return
	}

	renderx.JSON(w, http.StatusCreated, map[string]string{"message": fmt.Sprintf("created duckdb file for '%s' as '%s'", body.Path, tableName), "tableName": tableName})
}

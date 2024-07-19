package metrics

import (
	"github.com/factly/gopie/duckdb"
	"github.com/factly/gopie/pkg"
	"github.com/go-chi/chi/v5"
)

type httpHandler struct {
	logger *pkg.Logger
	conn   *duckdb.Connection
}

func (h *httpHandler) routes() chi.Router {
	router := chi.NewRouter()
	router.Get("/databases", h.list_databases)
	return router
}

func RegisterRoutes(router *chi.Mux, logger *pkg.Logger, conn *duckdb.Connection) {
	handler := httpHandler{logger, conn}
	router.Mount("/metrics", handler.routes())
}

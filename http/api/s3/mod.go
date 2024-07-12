package s3

import (
	"github.com/factly/gopie/duckdb"
	"github.com/factly/gopie/pkg"
	"github.com/go-chi/chi/v5"
)

type httpHandler struct {
	logger      *pkg.Logger
	objectStore duckdb.Transpoter
	conn        *duckdb.Connection
}

func RegisterRoutes(router *chi.Mux, logger *pkg.Logger, objectStore duckdb.Transpoter, conn *duckdb.Connection) {
	handler := httpHandler{logger, objectStore, conn}
	router.Mount("/source", handler.routes())
}

func (h *httpHandler) routes() chi.Router {
	router := chi.NewRouter()
	router.Post("/s3", h.create)
	router.Put("/s3", h.update)
	router.Delete("/s3", h.delete_)
	return router
}

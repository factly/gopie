package api

import (
	"github.com/factly/gopie/ai"
	"github.com/factly/gopie/duckdb"
	"github.com/factly/gopie/pkg"
	"github.com/go-chi/chi/v5"
)

type httpHandler struct {
	logger       *pkg.Logger
	conn         *duckdb.Connection
	openAIClient *ai.PortKeyClient
}

func (h *httpHandler) routes() chi.Router {
	router := chi.NewRouter()
	router.Get("/health", h.healthHandler)
	router.Post("/sql", h.sql)
	router.Get("/tables/{tableName}", h.rest)
	router.Get("/schema/{tableName}", h.schema)
	router.Post("/nl2sql", h.nl2sql)
	return router
}

func RegisterRoutes(router *chi.Mux, logger *pkg.Logger, conn *duckdb.Connection, openAIClient *ai.PortKeyClient) {
	handler := httpHandler{logger, conn, openAIClient}
	router.Mount("/api", handler.routes())
}

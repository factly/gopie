package api

import (
	"github.com/factly/gopie/ai"
	"github.com/factly/gopie/duckdb"
	"github.com/factly/gopie/metering"
	"github.com/factly/gopie/pkg"
	"github.com/go-chi/chi/v5"
)

type ingestEventParams struct {
	endpoint       string
	dataset        string
	method         string
	subject        string
	userID         string
	organisationID string
}

func ingestEvent(m *metering.MeteringClient, params ingestEventParams) {
	go func() {
		m.Ingest(params.endpoint, params.userID, params.organisationID, params.dataset, params.method, params.subject)
	}()
}

type httpHandler struct {
	logger       *pkg.Logger
	conn         *duckdb.Connection
	openAIClient *ai.PortKeyClient
	metering     *metering.MeteringClient
}

func (h *httpHandler) routes() chi.Router {
	router := chi.NewRouter()
	router.Post("/sql", h.sql)
	router.Get("/tables/{tableName}", h.rest)
	router.Get("/schema/{tableName}", h.schema)
	router.Post("/nl2sql", h.nl2sql)
	return router
}

func RegisterRoutes(router *chi.Mux, logger *pkg.Logger, conn *duckdb.Connection, openAIClient *ai.PortKeyClient, metering *metering.MeteringClient) {
	handler := httpHandler{logger, conn, openAIClient, metering}
	router.Mount("/api", handler.routes())
}

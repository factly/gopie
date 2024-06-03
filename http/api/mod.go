package api

import (
	"github.com/factly/gopie/pkg"
	"github.com/go-chi/chi/v5"
)

type httpHandler struct {
	logger pkg.Logger
}

type HttpHandlerInitInput struct {
	Logger pkg.Logger
}

func (h *httpHandler) routes() chi.Router {
	router := chi.NewRouter()
	router.Get("/health", h.healthHandler)
	router.Get("/sql", h.sql)
	return router
}

func RegisterRoutes(router *chi.Mux, input HttpHandlerInitInput) {
	handler := httpHandler{logger: input.Logger}
	router.Mount("/api", handler.routes())
}

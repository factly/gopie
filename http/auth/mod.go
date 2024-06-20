package auth

import (
	"github.com/factly/gopie/auth"
	"github.com/factly/gopie/pkg"
	"github.com/go-chi/chi/v5"
)

type httpHandler struct {
	logger *pkg.Logger
	a      auth.IAuth
}

type key struct {
	Key string `json:"apikey"`
}

func (h *httpHandler) routes() chi.Router {
	router := chi.NewRouter()
	router.Post("/apikey", h.create)
	router.Patch("/apikey", h.update)
	router.Delete("/apikey", h.delete_)
	router.Get("/apikey", h.list)
	router.Get("/apikey/details", h.details)
	router.Post("/apikey/invalidate", h.invalidate)
	return router
}

func RegisterAuthRoutes(router *chi.Mux, logger *pkg.Logger, a auth.IAuth) {
	handler := httpHandler{logger, a}
	router.Mount("/auth", handler.routes())
}

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
	Key string `json:"api_key"`
}

func (h *httpHandler) routes() chi.Router {
	router := chi.NewRouter()
	router.Post("/apikey/create", h.create)
	router.Patch("/apikey", h.update)
	router.Delete("/apikey", h.delete_)
	router.Route("/apikey", func(r chi.Router) {
		r.Post("/list", h.list)
		r.Post("/details", h.details)
		r.Post("/invalidate", h.invalidate)
	})
	return router
}

func RegisterAuthRoutes(router *chi.Mux, logger *pkg.Logger, a auth.IAuth) {
	handler := httpHandler{logger, a}
	router.Mount("/auth", handler.routes())
}

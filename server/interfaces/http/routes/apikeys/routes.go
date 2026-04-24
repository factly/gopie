package apikeys

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	logger        *logger.Logger
	apikeyService *services.ApikeyService
}

func Routes(router fiber.Router, apikeyService *services.ApikeyService, logger *logger.Logger) {
	h := &httpHandler{
		logger:        logger,
		apikeyService: apikeyService,
	}

	router.Use(middleware.RequireAdmin())
	router.Get("/", h.list)
	router.Post("/", h.create)
	router.Delete("/:id", h.delete)
}

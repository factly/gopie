package api

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	svc    *services.Driver
	logger *logger.Logger
}

func Routes(router fiber.Router, svc *services.Driver, logger *logger.Logger) {
	httpHandler := httpHandler{svc, logger}
	router.Post("/sql", httpHandler.sql)
}

package s3

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	svc    *services.OlapService
	logger *logger.Logger
}

func Routes(router fiber.Router, svc *services.OlapService, logger *logger.Logger) {
	httpHandler := httpHandler{svc, logger}
	router.Post("/upload", httpHandler.upload)
}

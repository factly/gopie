package download

import (
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"

	"github.com/factly/gopie/application/services"
)

type httpHandler struct {
	service *services.DownloadService
	logger  *logger.Logger
}

func Routes(router fiber.Router, service *services.DownloadService, logger *logger.Logger) {
	h := httpHandler{service, logger}
	router.Post("/downloads", h.createAndStream)
	router.Get("/downloads", h.list)
	router.Get("/downloads/:id", h.get)
	router.Delete("/downloads/:id", h.delete)
}

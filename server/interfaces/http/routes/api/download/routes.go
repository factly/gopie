package download

import (
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"

	"github.com/factly/gopie/application/services"
)

type httpHandler struct {
	service *services.DownloadsService
	logger  *logger.Logger
}

func Routes(router fiber.Router, service *services.DownloadsService, logger *logger.Logger) {
	h := httpHandler{service, logger}
	router.Post("/", h.createAndStream)
	router.Get("/", h.list)
	router.Get("/:id", h.get)
	router.Delete("/:id", h.delete)
}

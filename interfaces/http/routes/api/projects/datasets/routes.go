package datasets

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	logger *logger.Logger
	svc    *services.DatasetService
}

// Routes - Route configuration for datasets
func Routes(router fiber.Router, svc *services.DatasetService, logger *logger.Logger) {
	httpHandler := httpHandler{logger, svc}
	router.Get("/", httpHandler.list)
	router.Get("/:datasetID", httpHandler.details)
	router.Delete("/:datasetID", httpHandler.delete)
}

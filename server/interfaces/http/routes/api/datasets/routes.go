package datasets

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	datasetsSvc *services.DatasetService
	logger      *logger.Logger
}

// NewHTTPHandler creates a new HTTP handler for datasets
func NewHTTPHandler(router fiber.Router, datasetsSvc *services.DatasetService, logger *logger.Logger) {
	handler := &httpHandler{
		datasetsSvc: datasetsSvc,
		logger:      logger,
	}

	// Setup routes
	datasetsRouter := router.Group("/datasets")
	datasetsRouter.Get("/:datasetID", handler.details)
}

func NewHTTPHandlerInternal(router fiber.Router, datasetsSvc *services.DatasetService, logger *logger.Logger) {
	handler := &httpHandler{
		datasetsSvc: datasetsSvc,
		logger:      logger,
	}

	datasetsRouter := router.Group("/datasets")
	datasetsRouter.Get("/:datasetID", handler.getByID)
}

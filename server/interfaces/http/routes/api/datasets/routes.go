package datasets

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	datasetsSvc *services.DatasetService
	olapSvc     *services.OlapService
	logger      *logger.Logger
}

// NewHTTPHandler creates a new HTTP handler for datasets
func NewHTTPHandler(router fiber.Router, datasetsSvc *services.DatasetService, olapSvc *services.OlapService, logger *logger.Logger) {
	handler := &httpHandler{
		datasetsSvc: datasetsSvc,
		olapSvc:     olapSvc,
		logger:      logger,
	}

	// Setup routes
	datasetsRouter := router.Group("/datasets")
	datasetsRouter.Get("/:datasetID", handler.details)
	datasetsRouter.Get("/:datasetID/project", handler.getProjectForDataset)
	datasetsRouter.Get("/:datasetID/column-descriptions", handler.getColumnDescriptions)
	datasetsRouter.Patch("/:datasetID/column-descriptions", handler.updateColumnDescriptions)
}

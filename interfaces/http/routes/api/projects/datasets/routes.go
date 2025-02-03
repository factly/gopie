package datasets

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	logger *logger.Logger
	svc    *services.DatasetService
}

// Routes - Route configuration for datasets
func Routes(router fiber.Router, svc *services.DatasetService, projectSvc *services.ProjectService, logger *logger.Logger) {
	httpHandler := httpHandler{logger, svc}

	// Add project validation middleware to all dataset routes
	router.Use(middleware.ValidateProjectMiddleware(projectSvc))

	router.Get("/", httpHandler.list)
	router.Get("/:datasetID", httpHandler.details)
	router.Delete("/:datasetID", httpHandler.delete)
}

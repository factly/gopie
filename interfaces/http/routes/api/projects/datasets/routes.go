package datasets

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	logger      *logger.Logger
	datasetsSvc *services.DatasetService
	olapSvc     *services.OlapService
}

type RouterParams struct {
	Logger      *logger.Logger
	DatasetSvc  *services.DatasetService
	ProjectSvc  *services.ProjectService
	OlapService *services.OlapService
}

// Routes - Route configuration for datasets
func Routes(router fiber.Router, params RouterParams) {
	httpHandler := httpHandler{logger: params.Logger, datasetsSvc: params.DatasetSvc, olapSvc: params.OlapService}

	// Add project validation middleware to all dataset routes
	router.Use(middleware.ValidateProjectMiddleware(params.ProjectSvc))

	router.Get("/", httpHandler.list)
	router.Get("/:datasetID", httpHandler.details)
	router.Delete("/:datasetID", httpHandler.delete)
}

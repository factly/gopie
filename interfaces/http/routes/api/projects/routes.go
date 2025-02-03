package projects

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/factly/gopie/interfaces/http/routes/api/projects/datasets"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	logger *logger.Logger
	svc    *services.ProjectService
}

func Routes(router fiber.Router, svc *services.ProjectService, datasetService *services.DatasetService, logger *logger.Logger) {
	httpHandler := httpHandler{logger, svc}
	router.Get("/", httpHandler.list)
	router.Post("/", middleware.ValidateReqBodyMiddleware(new(createRequestBody)), httpHandler.create)
	router.Get("/:projectID", httpHandler.details)
	router.Patch("/:projectID", middleware.ValidateReqBodyMiddleware(new(updateProjectBody)), httpHandler.update)
	router.Delete("/:projectID", httpHandler.delete)
	datasets.Routes(router.Group("/:projectID/datasets"), datasetService, svc, logger)
}

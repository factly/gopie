package s3

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	logger     *logger.Logger
	olapSvc    *services.OlapService
	datasetSvc *services.DatasetService
	projectSvc *services.ProjectService
}

func Routes(router fiber.Router, olapSvc *services.OlapService, datasetSvc *services.DatasetService, projectSvc *services.ProjectService, logger *logger.Logger) {
	httpHandler := httpHandler{logger, olapSvc, datasetSvc, projectSvc}
	router.Post("/upload", middleware.ValidateReqBodyMiddleware(new(uploadRequestBody)), httpHandler.upload)
}

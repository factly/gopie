package s3

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	olapSvc    *services.OlapService
	logger     *logger.Logger
	datasetSvc *services.DatasetService
}

func Routes(router fiber.Router, svc *services.OlapService, datasetSvc *services.DatasetService, logger *logger.Logger) {
	httpHandler := httpHandler{svc, logger, datasetSvc}
	router.Post("/upload", httpHandler.upload)
}

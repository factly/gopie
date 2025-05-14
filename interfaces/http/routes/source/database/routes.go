package database

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	logger      *logger.Logger
	olapSvc     *services.OlapService
	datasetSvc  *services.DatasetService
	aiAgentSvc  *services.AIService
	projectSvc  *services.ProjectService
	dbSourceSvc *services.DatabaseSourceService
}

func Routes(
	router fiber.Router,
	olapSvc *services.OlapService,
	datasetSvc *services.DatasetService,
	projectSvc *services.ProjectService,
	aiAgent *services.AIService,
	dbSourceSvc *services.DatabaseSourceService,
	logger *logger.Logger,
) {
	httpHandler := httpHandler{
		logger:      logger,
		olapSvc:     olapSvc,
		datasetSvc:  datasetSvc,
		aiAgentSvc:  aiAgent,
		projectSvc:  projectSvc,
		dbSourceSvc: dbSourceSvc,
	}

	router.Post("/create", httpHandler.create)
}

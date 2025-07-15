package projects

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/interfaces/http/routes/api/projects/datasets"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	logger      *logger.Logger
	projectSvc  *services.ProjectService
	datasetSvc  *services.DatasetService
	olapService *services.OlapService
}

type RouterParams struct {
	Logger         *logger.Logger
	ProjectService *services.ProjectService
	DatasetService *services.DatasetService
	OlapService    *services.OlapService
	AiAgentService *services.AIService
}

func Routes(router fiber.Router, params RouterParams) {
	httpHandler := httpHandler{
		logger:      params.Logger,
		projectSvc:  params.ProjectService,
		datasetSvc:  params.DatasetService,
		olapService: params.OlapService,
	}
	router.Get("/", httpHandler.list)
	router.Post("/", httpHandler.create)
	router.Get("/:projectID", httpHandler.details)
	router.Get("/:projectID/openapi", httpHandler.projectOpenAPI)
	router.Patch("/:projectID", httpHandler.update)
	router.Delete("/:projectID", httpHandler.delete)
	datasets.Routes(router.Group("/:projectID/datasets"), datasets.RouterParams{
		Logger:      params.Logger,
		DatasetSvc:  params.DatasetService,
		OlapService: params.OlapService,
		ProjectSvc:  params.ProjectService,
		AiAgentSvc:  params.AiAgentService,
	})
}

func InternalRoutes(router fiber.Router, params RouterParams) {
	httpHandler := httpHandler{
		logger:      params.Logger,
		projectSvc:  params.ProjectService,
		datasetSvc:  params.DatasetService,
		olapService: params.OlapService,
	}
	router.Get("/:projectID", httpHandler.getByID)
	datasets.InternalRoutes(router.Group("/:projectID/datasets"), datasets.RouterParams{
		Logger:      params.Logger,
		DatasetSvc:  params.DatasetService,
		OlapService: params.OlapService,
		ProjectSvc:  params.ProjectService,
		AiAgentSvc:  params.AiAgentService,
	})
}

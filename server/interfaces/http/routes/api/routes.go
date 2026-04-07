package api

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/factly/gopie/interfaces/http/routes/api/datasets"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	olapSvc     *services.OlapService
	datasetsSvc *services.DatasetService
	projectSvc  *services.ProjectService
	aiSvc       *services.AiDriver
	logger      *logger.Logger
	config      *config.GopieConfig
}

func Routes(router fiber.Router, driverSvc *services.OlapService, aiSvc *services.AiDriver, datasetsSvc *services.DatasetService, projectSvc *services.ProjectService, aiAgentSvc *services.AIService, logger *logger.Logger) {
	// Use middleware to authorize datasets from params
	router.Use(middleware.AuthorizeDatasetsFromParams(projectSvc, logger))

	httpHandler := httpHandler{driverSvc, datasetsSvc, projectSvc, aiSvc, logger, nil}
	// /sql endpoint with middleware to authorize datasets from sql query
	router.Post("/sql", middleware.AuthorizeDatasetsAccessFromSql(driverSvc, projectSvc, logger), httpHandler.sql)
	router.Post("/tables/:tableName", httpHandler.rest)
	router.Post("/nl2sql", httpHandler.nl2sql)
	router.Get("/schemas/:tableName", httpHandler.schemas)
	router.Get("/summary/:tableName", httpHandler.summary)
	// Add OpenAPI specification endpoint
	router.Get("/openapi/:tableName", httpHandler.datasetOpenAPI)

	// Register datasets routes
	datasets.NewHTTPHandler(router, datasetsSvc, driverSvc, aiAgentSvc, logger)
}

func InternalRoutes(router fiber.Router, driverSvc *services.OlapService, aiSvc *services.AiDriver, datasetsSvc *services.DatasetService, projectSvc *services.ProjectService, logger *logger.Logger) {
	httpHandler := httpHandler{driverSvc, datasetsSvc, projectSvc, aiSvc, logger, nil}
	router.Post("/sql", httpHandler.sql)
	router.Post("/tables/:tableName", httpHandler.rest)
	router.Post("/nl2sql", httpHandler.nl2sql)
	router.Get("/schemas/:tableName", httpHandler.schemas)
	router.Get("/summary/:tableName", httpHandler.summary)
}

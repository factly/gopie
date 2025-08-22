package api

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/interfaces/http/routes/api/datasets"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	driverSvc *services.OlapService
	aiSvc     *services.AiDriver
	logger    *logger.Logger
	config    *config.GoPieConfig
}

func Routes(router fiber.Router, driverSvc *services.OlapService, aiSvc *services.AiDriver, datasetsSvc *services.DatasetService, logger *logger.Logger) {
	httpHandler := httpHandler{driverSvc, aiSvc, logger, nil}
	router.Post("/sql", httpHandler.sql)
	router.Get("/tables/:tableName", httpHandler.rest)
	router.Post("/nl2sql", httpHandler.nl2sql)
	router.Get("/schemas/:tableName", httpHandler.schemas)
	router.Get("/summary/:tableName", httpHandler.summary)
	// Add OpenAPI specification endpoint
	router.Get("/openapi/:tableName", httpHandler.datasetOpenAPI)

	// Register datasets routes
	datasets.NewHTTPHandler(router, datasetsSvc, driverSvc, logger)
}

func AuthRoutes(router fiber.Router, logger *logger.Logger, config *config.GoPieConfig) {
	// httpHandler := httpHandler{logger: logger, config: config}
	// router.Post("/authorize", httpHandler.authorize)
}

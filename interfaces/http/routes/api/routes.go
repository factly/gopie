package api

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	driverSvc *services.Driver
	aiSvc     *services.AiDriver
	logger    *logger.Logger
}

func Routes(router fiber.Router, driverSvc *services.Driver, aiSvc *services.AiDriver, logger *logger.Logger) {
	httpHandler := httpHandler{driverSvc, aiSvc, logger}
	router.Post("/sql", httpHandler.sql)
	router.Get("/tables/:tableName", httpHandler.rest)
	router.Post("/nl2sql", httpHandler.nl2sql)
	router.Get("/schema/:tableName", httpHandler.schema)
}

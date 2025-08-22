package ai

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	logger *logger.Logger
	aiSvc  *services.AiDriver
}

func Routes(router fiber.Router, aiService *services.AiDriver, logger *logger.Logger) {
	httpHandler := httpHandler{
		logger: logger,
		aiSvc:  aiService,
	}

	router.Post("/generate-column-descriptions", httpHandler.genColumnsDesc)
	router.Post("/generate-dataset-description", httpHandler.genDatasetDesc)
}

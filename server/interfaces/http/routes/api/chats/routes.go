package chats

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/gofiber/fiber/v2"
)

type httpHandler struct {
	logger     *logger.Logger
	chatSvc    *services.ChatService
	olapSvc    *services.OlapService
	datasetSvc *services.DatasetService
}

type RouterParams struct {
	Logger         *logger.Logger
	ChatService    *services.ChatService
	OlapService    *services.OlapService
	DatasetService *services.DatasetService
}

func Routes(router fiber.Router, params RouterParams) {
	httpHandler := httpHandler{
		logger:     params.Logger,
		chatSvc:    params.ChatService,
		olapSvc:    params.OlapService,
		datasetSvc: params.DatasetService,
	}
	router.Post("/", httpHandler.chat)
	router.Get("/", httpHandler.listUserChats)
	router.Post("/completions", httpHandler.chatWithAgent)
	router.Get("/:chatID/messages", httpHandler.getChatMessages)
	router.Delete("/:chatID", httpHandler.deleteChat)
}

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
	projectSvc *services.ProjectService
}

type RouterParams struct {
	Logger         *logger.Logger
	ChatService    *services.ChatService
	OlapService    *services.OlapService
	DatasetService *services.DatasetService
	ProjectService *services.ProjectService
}

func Routes(router fiber.Router, params RouterParams) {
	httpHandler := httpHandler{
		logger:     params.Logger,
		chatSvc:    params.ChatService,
		olapSvc:    params.OlapService,
		datasetSvc: params.DatasetService,
		projectSvc: params.ProjectService,
	}
	// Static routes first
	router.Get("/", httpHandler.listUserChats)
	router.Post("/create", httpHandler.createChat)
	router.Post("/completions", httpHandler.chatWithAgent)

	// Parameterized routes after static routes
	router.Get("/:chatID/messages", httpHandler.getChatMessages)
	router.Put("/:chatID/visibility", httpHandler.updateVisibility)
	router.Put("/:chatID/title", httpHandler.updateTitle)
	router.Get("/:chatID", httpHandler.details)
	router.Delete("/:chatID", httpHandler.deleteChat)
}

package routes

import (
	"github.com/factly/gopie/downlods-server/pkg/logger"
	"github.com/factly/gopie/downlods-server/queue"
	"github.com/gofiber/fiber/v2"
)

// httpHandler holds the dependencies for your API handlers.
type httpHandler struct {
	logger *logger.Logger
	queue  *queue.DownloadQueue
}

func NewHttpHandler(log *logger.Logger, queue *queue.DownloadQueue) *httpHandler {
	return &httpHandler{
		logger: log,
		queue:  queue,
	}
}

// RegisterRoutes sets up all the application routes on the provided fiber router.
func (h *httpHandler) RegisterRoutes(router fiber.Router) {
	router.Get("/health", h.healthCheck)
	router.Post("/downloads", h.createDownload)
	router.Get("/downloads", h.listDownloads)
	router.Get("/downloads/:id", h.getDownload)
	router.Delete("/downloads/:id", h.deleteDownload)
}

func (h *httpHandler) healthCheck(c *fiber.Ctx) error {
	return c.JSON("Ok")
}

package routes

import (
	_ "github.com/factly/gopie/downlods-server/docs" // Import generated docs
	"github.com/factly/gopie/downlods-server/pkg/logger"
	"github.com/factly/gopie/downlods-server/queue"
	"github.com/gofiber/fiber/v2"
	fiberSwagger "github.com/swaggo/fiber-swagger"
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

// RegisterPublicRoutes sets up routes that don't require authentication
func (h *httpHandler) RegisterPublicRoutes(router fiber.Router) {
	// Swagger documentation
	router.Get("/swagger", func(c *fiber.Ctx) error {
		return c.Redirect("/swagger/index.html")
	})
	router.Get("/swagger/*", fiberSwagger.WrapHandler)

	// Health check
	router.Get("/health", h.healthCheck)
}

// RegisterProtectedRoutes sets up routes that require authentication
func (h *httpHandler) RegisterProtectedRoutes(router fiber.Router) {
	// Downloads API routes
	router.Post("/downloads", h.createDownload)
	router.Get("/downloads", h.listDownloads)
	router.Get("/downloads/:id", h.getDownload)
	router.Delete("/downloads/:id", h.deleteDownload)
}

// RegisterRoutes sets up all the application routes on the provided fiber router.
// Deprecated: Use RegisterPublicRoutes and RegisterProtectedRoutes instead
func (h *httpHandler) RegisterRoutes(router fiber.Router) {
	h.RegisterPublicRoutes(router)
	h.RegisterProtectedRoutes(router)
}

// healthCheck checks if the service is running
// @Summary Health check
// @Description Check if the service is running
// @Tags Health
// @Produce json
// @Success 200 {string} string "Service is healthy"
// @Router /health [get]
func (h *httpHandler) healthCheck(c *fiber.Ctx) error {
	return c.JSON("Ok")
}

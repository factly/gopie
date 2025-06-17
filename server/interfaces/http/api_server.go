package http

import (
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/gofiber/contrib/fiberzap"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"go.uber.org/zap"
)

// serveApiServer starts the API server with the given configuration
func serveApiServer(cfg *config.GopieConfig, params *ServerParams) error {
	log := params.Logger
	app := fiber.New(fiber.Config{
		CaseSensitive: true,
		AppName:       "gopie-api",
	})

	// Apply middleware
	app.Use(cors.New(cors.Config{
		AllowOrigins:     "http://localhost:3000,https://gopie.factly.dev,https://*.factly.dev",
		AllowMethods:     "GET,POST,HEAD,PUT,DELETE,PATCH,OPTIONS",
		AllowHeaders:     "Origin, Content-Type, Accept, Authorization, X-Requested-With, X-CSRF-Token, userID, x-user-id, x-project-ids, x-dataset-ids, x-chat-id",
		AllowCredentials: true,
		MaxAge:           86400,
	}))

	app.Use(fiberzap.New(fiberzap.Config{
		Logger: log.Logger,
	}))

	// Health check endpoint
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status": "ok",
		})
	})

	// Start the server
	addr := ":" + cfg.ApiServer.Port
	log.Info("API server starting",
		zap.String("host", cfg.ApiServer.Host),
		zap.String("port", cfg.ApiServer.Port))

	return app.Listen(addr)
}

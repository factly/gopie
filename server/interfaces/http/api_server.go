package http

import (
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/interfaces/http/routes/api"
	chatApi "github.com/factly/gopie/interfaces/http/routes/api/chats"
	projectApi "github.com/factly/gopie/interfaces/http/routes/api/projects"
	databaseRoutes "github.com/factly/gopie/interfaces/http/routes/source/database"
	s3Routes "github.com/factly/gopie/interfaces/http/routes/source/s3"
	"github.com/gofiber/contrib/fiberzap"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/swagger"
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

	// Swagger route
	app.Get("/swagger/*", swagger.HandlerDefault)

	if cfg.OlapDB.AccessMode != "read_only" {
		params.Logger.Info("Initializing read-write routes...")

		// S3 routes
		s3Routes.Routes(app.Group("/source/s3"), params.OlapService, params.DatasetService, params.ProjectService, params.AIAgentService, params.Logger)

		// Database source routes
		databaseRoutes.Routes(
			app.Group("/source/database"),
			params.OlapService,
			params.DatasetService,
			params.ProjectService,
			params.AIAgentService,
			params.DbSourceService,
			params.Logger,
		)
	} else {
		params.Logger.Info("Running in read-only mode, write endpoints are disabled")
	}

	api.Routes(app.Group("/v1/api"), params.OlapService, params.AIService, params.DatasetService, params.Logger)

	projectApi.Routes(app.Group("/v1/api/projects"), projectApi.RouterParams{
		Logger:         params.Logger,
		ProjectService: params.ProjectService,
		DatasetService: params.DatasetService,
		OlapService:    params.OlapService,
	})
	chatApi.Routes(app.Group("/v1/api/chat"), chatApi.RouterParams{
		Logger:         params.Logger,
		ChatService:    params.ChatService,
		DatasetService: params.DatasetService,
		OlapService:    params.OlapService,
	})

	// Start the server
	addr := ":" + cfg.ApiServer.Port
	log.Info("API server starting",
		zap.String("host", cfg.ApiServer.Host),
		zap.String("port", cfg.ApiServer.Port))

	return app.Listen(addr)
}

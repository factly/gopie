package http

import (
	"context"

	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/infrastructure/zitadel"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/factly/gopie/interfaces/http/routes/api"
	"github.com/factly/gopie/interfaces/http/routes/api/ai"
	chatApi "github.com/factly/gopie/interfaces/http/routes/api/chats"
	"github.com/factly/gopie/interfaces/http/routes/api/download"
	projectApi "github.com/factly/gopie/interfaces/http/routes/api/projects"
	databaseRoutes "github.com/factly/gopie/interfaces/http/routes/source/database"
	s3Routes "github.com/factly/gopie/interfaces/http/routes/source/s3"
	"github.com/gofiber/contrib/fiberzap"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/swagger"
	"go.uber.org/zap"
)

// serve starts the web application server
func serve(cfg *config.GoPieConfig, params *ServerParams, ctx context.Context) error {
	var authMiddleware []fiber.Handler
	if cfg.EnableZitadel {
		// zitadel interceptor setup
		params.Logger.Info("Zitadel is enabled, setting up zitadel interceptor")
		zitadel.SetupZitadelInterceptor(cfg, params.Logger)
		authMiddleware = []fiber.Handler{middleware.ZitadelAuthorizer(params.Logger), middleware.ZitadelAuth(params.Logger)}
	} else {
		params.Logger.Info("Zitadel is disabled, setting up authorize headers interceptor")
		authMiddleware = []fiber.Handler{middleware.AuthorizeHeaders(params.Logger)}
	}

	appLogger := params.Logger

	appLogger.Info("Initializing main server",
		zap.String("host", cfg.Server.Host),
		zap.String("port", cfg.Server.Port))

	app := fiber.New(fiber.Config{
		CaseSensitive: true,
		AppName:       "gopie",
	})

	app.Use(cors.New(cors.Config{
		AllowOrigins:     "http://localhost:3000,https://gopie.factly.dev,https://*.factly.dev,https://gopie-web.vercel.app",
		AllowMethods:     "GET,POST,HEAD,PUT,DELETE,PATCH,OPTIONS",
		AllowHeaders:     "Origin, Content-Type, Accept, Authorization, X-Requested-With, X-CSRF-Token, userID, x-user-id, x-project-ids, x-dataset-ids, x-chat-id, x-organization-id",
		AllowCredentials: true,
		MaxAge:           86400,
	}))

	app.Use(fiberzap.New(fiberzap.Config{
		Logger: appLogger.Logger,
	}))

	// Impose limits on web facing apis
	app.Use(middleware.ImposeLimit(true))

	// Swagger route
	app.Get("/swagger/*", swagger.HandlerDefault)

	// auth route
	api.AuthRoutes(app.Group("/v1/oauth"), appLogger, cfg)

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status": "ok",
		})
	})

	if cfg.OlapDB.AccessMode != "read_only" {
		appLogger.Info("Initializing read-write routes...")

		sourceGroup := app.Group("/source", authMiddleware...)
		// S3 routes
		s3Routes.Routes(sourceGroup.Group("/s3"), params.OlapService, params.DatasetService, params.ProjectService, params.AIAgentService, appLogger)

		// Database source routes
		databaseRoutes.Routes(
			sourceGroup.Group("/database"),
			params.OlapService,
			params.DatasetService,
			params.ProjectService,
			params.AIAgentService,
			params.DbSourceService,
			appLogger,
		)
	} else {
		appLogger.Info("Running in read-only mode, write endpoints are disabled")
	}

	// Setup API routes
	appLogger.Info("Setting up API routes...")

	apiGroup := app.Group("/v1/api", authMiddleware...)

	// AI routes
	ai.Routes(apiGroup.Group("/ai"), params.AIService, appLogger)

	// Main API routes
	api.Routes(apiGroup, params.OlapService, params.AIService, params.DatasetService, appLogger)

	// Project routes
	projectApi.Routes(apiGroup.Group("/projects"), projectApi.RouterParams{
		Logger:         appLogger,
		ProjectService: params.ProjectService,
		DatasetService: params.DatasetService,
		OlapService:    params.OlapService,
		AiAgentService: params.AIAgentService,
	})

	// Chat routes
	chatApi.Routes(apiGroup.Group("/chat"), chatApi.RouterParams{
		Logger:         appLogger,
		ChatService:    params.ChatService,
		DatasetService: params.DatasetService,
		OlapService:    params.OlapService,
	})
	download.Routes(apiGroup.Group("/downloads"),
		params.DownloadsService,
		appLogger,
	)

	// Create a channel to listen for server shutdown
	serverShutdown := make(chan struct{})

	// Start the server in a goroutine
	go func() {
		addr := ":" + cfg.Server.Port
		appLogger.Info("Main server is starting...",
			zap.String("host", cfg.Server.Host),
			zap.String("port", cfg.Server.Port))

		if err := app.Listen(addr); err != nil {
			appLogger.Error("Main server error", zap.Error(err))
		}
		close(serverShutdown)
	}()

	// Wait for context cancellation or server shutdown
	select {
	case <-ctx.Done():
		appLogger.Info("Shutdown signal received, gracefully shutting down...")
		if err := app.Shutdown(); err != nil {
			appLogger.Error("Error during server shutdown", zap.Error(err))
			return err
		}
	case <-serverShutdown:
		appLogger.Info("Server stopped")
	}

	return nil
}

func serveInternal(cfg *config.GoPieConfig, params *ServerParams, ctx context.Context) error {
	appLogger := params.Logger

	appLogger.Info("Initializing internal server",
		zap.String("host", cfg.InternalServer.Host),
		zap.String("port", cfg.InternalServer.Port),
	)

	app := fiber.New(fiber.Config{
		CaseSensitive: true,
		AppName:       "gopie-internal",
	})

	app.Use(cors.New(cors.Config{
		AllowOrigins:     "http://localhost:3000,https://gopie.factly.dev,https://*.factly.dev,https://gopie-web.vercel.app",
		AllowMethods:     "GET,POST,HEAD,PUT,DELETE,PATCH,OPTIONS",
		AllowHeaders:     "Origin, Content-Type, Accept, Authorization, X-Requested-With, X-CSRF-Token, userID, x-user-id, x-project-ids, x-dataset-ids, x-chat-id, x-organization-id",
		AllowCredentials: true,
		MaxAge:           86400,
	}))

	app.Use(fiberzap.New(fiberzap.Config{
		Logger: appLogger.Logger,
	}))

	// Don't impose limits on internal server
	app.Use(middleware.ImposeLimit(false))

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status": "ok",
		})
	})

	apiGroup := app.Group("/v1/api")

	api.Routes(apiGroup, params.OlapService, params.AIService, params.DatasetService, appLogger)

	projectApi.InternalRoutes(apiGroup.Group("/projects"), projectApi.RouterParams{
		Logger:         appLogger,
		ProjectService: params.ProjectService,
		DatasetService: params.DatasetService,
		OlapService:    params.OlapService,
		AiAgentService: params.AIAgentService,
	})

	// Create a channel to listen for server shutdown
	serverShutdown := make(chan struct{})

	// Start the server in a goroutine
	go func() {
		addr := ":" + cfg.InternalServer.Port
		appLogger.Info("Internal server is starting...",
			zap.String("host", cfg.InternalServer.Host),
			zap.String("port", cfg.InternalServer.Port))

		if err := app.Listen(addr); err != nil {
			appLogger.Error("Internal server error", zap.Error(err))
		}
		close(serverShutdown)
	}()

	// Wait for context cancellation or server shutdown
	select {
	case <-ctx.Done():
		appLogger.Info("Shutdown signal received, gracefully shutting down...")
		if err := app.Shutdown(); err != nil {
			appLogger.Error("Error during server shutdown", zap.Error(err))
			return err
		}
	case <-serverShutdown:
		appLogger.Info("Server stopped")
	}

	return nil
}

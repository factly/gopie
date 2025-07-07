package http

import (
	"context"

	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/infrastructure/zitadel"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/factly/gopie/interfaces/http/routes/api"
	"github.com/factly/gopie/interfaces/http/routes/api/ai"
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

// serveWebApp starts the web application server
func serveWebApp(cfg *config.GopieConfig, params *ServerParams, ctx context.Context) error {
	// zitadel interceptor setup
	zitadel.SetupZitadelInterceptor(cfg, params.Logger)

	appLogger := params.Logger

	appLogger.Info("Initializing main server",
		zap.String("host", cfg.Server.Host),
		zap.String("port", cfg.Server.Port))

	app := fiber.New(fiber.Config{
		CaseSensitive: true,
		AppName:       "gopie",
	})

	app.Use(cors.New(cors.Config{
		AllowOrigins:     "http://localhost:3000,https://gopie.factly.dev,https://*.factly.dev",
		AllowMethods:     "GET,POST,HEAD,PUT,DELETE,PATCH,OPTIONS",
		AllowHeaders:     "Origin, Content-Type, Accept, Authorization, X-Requested-With, X-CSRF-Token, userID, x-user-id, x-project-ids, x-dataset-ids, x-chat-id, x-organization-id",
		AllowCredentials: true,
		MaxAge:           86400,
	}))

	app.Use(fiberzap.New(fiberzap.Config{
		Logger: appLogger.Logger,
	}))

	// Swagger route
	app.Get("/swagger/*", swagger.HandlerDefault)

	// auth route
	api.AuthRoutes(app.Group("/v1/oauth"), appLogger, cfg)

	// // Only enable authorization if meterus is configured
	// if cfg.Meterus.ApiKey == "" || cfg.Meterus.Addr == "" {
	// 	appLogger.Warn("meterus is not configured, authorization will be disabled")
	// } else {
	// 	appLogger.Info("meterus config found, initializing...")
	// 	meterusClient, err := client.NewMeterusClient(cfg.Meterus.Addr, cfg.Meterus.ApiKey)
	// 	if err != nil {
	// 		appLogger.Error("error creating meterus client", zap.Error(err))
	// 		return err
	// 	}
	// 	appLogger.Info("meterus client created")
	// 	meterusValidator := meterus.NewMeterusApiKeyValidator(meterusClient)
	// 	app.Use(middleware.WithApiKeyAuth(meterusValidator, appLogger))
	// }

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status": "ok",
		})
	})

	if cfg.OlapDB.AccessMode != "read_only" {
		appLogger.Info("Initializing read-write routes...")

		sourceGroup := app.Group("/source", middleware.ZitadelAuthorizer(appLogger), middleware.SetupZitadelAuthCtx(appLogger))
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

	apiGroup := app.Group("/v1/api", middleware.ZitadelAuthorizer(appLogger), middleware.SetupZitadelAuthCtx(appLogger))

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

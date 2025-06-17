package http

import (
	"context"
	"log"
	"sync"

	"github.com/elliot14A/meterus-go/client"
	"github.com/factly/gopie/application/services"
	_ "github.com/factly/gopie/docs" // Import generated Swagger docs
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/aiagent"
	"github.com/factly/gopie/infrastructure/duckdb"
	"github.com/factly/gopie/infrastructure/meterus"
	"github.com/factly/gopie/infrastructure/portkey"
	"github.com/factly/gopie/infrastructure/postgres/store"
	"github.com/factly/gopie/infrastructure/postgres/store/chats"
	"github.com/factly/gopie/infrastructure/postgres/store/database_source"
	"github.com/factly/gopie/infrastructure/postgres/store/datasets"
	"github.com/factly/gopie/infrastructure/postgres/store/projects"
	"github.com/factly/gopie/infrastructure/s3"
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

// @title GoPie API
// @version 1.1
// @description GoPie API documentation
// @host localhost:8000
// @BasePath /
func ServeHttp() error {
	// Load configuration
	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatal("error loading config: ", err)
		return err
	}

	// Initialize logger
	appLogger, err := logger.NewLogger(
		map[string]any{
			"log_level": cfg.Logger.Level,
			"mode":      cfg.Logger.Mode,
			"log_file":  cfg.Logger.LogFile,
		},
	)
	if err != nil {
		log.Fatal("error initializing logger: ", err)
		return err
	}

	// Initialize repositories and services
	source := s3.NewS3SourceRepository(&cfg.S3, appLogger)
	olap, err := duckdb.NewOlapDBDriver(&cfg.OlapDB, appLogger, &cfg.S3)
	if err != nil {
		appLogger.Error("error connecting to olap database", zap.Error(err))
		return err
	}

	porkeyClient := portkey.NewPortKeyClient(cfg.PortKey, appLogger)

	// Store setup
	storeRepo := store.NewPostgresStoreRepository(appLogger)
	err = storeRepo.Connect(&cfg.Postgres)
	if err != nil {
		appLogger.Error("error connecting to postgres", zap.Error(err))
		return err
	}

	// Initialize repositories
	projectStore := projects.NewPostgresProjectStore(storeRepo.GetDB(), appLogger)
	datasetStore := datasets.NewPostgresDatasetStore(storeRepo.GetDB(), appLogger)
	chatStore := chats.NewChatStoreRepository(storeRepo.GetDB(), appLogger)
	dbSourceStore := database_source.NewDatabaseSourceStore(storeRepo.GetDB(), appLogger, cfg)
	aiAgentRepo := aiagent.NewAIAgent(cfg.AIAgent.Url, appLogger)

	olapService := services.NewOlapService(olap, source, appLogger)
	// Initialize services
	aiService := services.NewAiDriver(porkeyClient)
	projectService := services.NewProjectService(projectStore)
	datasetService := services.NewDatasetService(datasetStore)
	chatService := services.NewChatService(chatStore, porkeyClient, aiAgentRepo)
	aiAgentService := services.NewAIService(aiAgentRepo)
	dbSourceService := services.NewDatabaseSourceService(dbSourceStore, appLogger)

	// Create ServerParams to pass to both servers
	params := &ServerParams{
		Logger:          appLogger,
		OlapService:     olapService,
		AIService:       aiService,
		ProjectService:  projectService,
		DatasetService:  datasetService,
		ChatService:     chatService,
		AIAgentService:  aiAgentService,
		DbSourceService: dbSourceService,
	}

	// Create a wait group to wait for both servers to shut down
	var wg sync.WaitGroup
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Start the API server in a separate goroutine if enabled
	if cfg.ApiServerOnly {
		appLogger.Info("Starting in api-server-only mode,web-client server will not be started")
	} else {
		wg.Add(1)
		go func() {
			defer wg.Done()
			appLogger.Info("Starting API server...")
			if err := webClientServer(cfg, params, ctx); err != nil {
				appLogger.Error("API server error", zap.Error(err))
				cancel()
			}
		}()
	}

	// Start the main server in the main goroutine
	appLogger.Info("Starting api server...")
	if err := serveApiServer(cfg, params); err != nil {
		appLogger.Error("api server error", zap.Error(err))
		cancel()
	}

	// Wait for both servers to shut down
	wg.Wait()
	return nil
}

// webClientServer starts the main application server
func webClientServer(cfg *config.GopieConfig, params *ServerParams, ctx context.Context) error {
	// zitadel interceptor setup
	// zitadel.SetupZitadelInterceptor(cfg, appLogger)

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
		AllowHeaders:     "Origin, Content-Type, Accept, Authorization, X-Requested-With, X-CSRF-Token, userID, x-user-id, x-project-ids, x-dataset-ids, x-chat-id",
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

	// Only enable authorization if meterus is configured
	if cfg.Meterus.ApiKey == "" || cfg.Meterus.Addr == "" {
		appLogger.Warn("meterus is not configured, authorization will be disabled")
	} else {
		appLogger.Info("meterus config found, initializing...")
		meterusClient, err := client.NewMeterusClient(cfg.Meterus.Addr, cfg.Meterus.ApiKey)
		if err != nil {
			appLogger.Error("error creating meterus client", zap.Error(err))
			return err
		}
		appLogger.Info("meterus client created")
		meterusValidator := meterus.NewMeterusApiKeyValidator(meterusClient)
		app.Use(middleware.WithApiKeyAuth(meterusValidator, appLogger))
	}

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status": "ok",
		})
	})

	if cfg.OlapDB.AccessMode != "read_only" {
		appLogger.Info("Initializing read-write routes...")

		// S3 routes
		s3Routes.Routes(app.Group("/source/s3"), params.OlapService, params.DatasetService, params.ProjectService, params.AIAgentService, appLogger)

		// Database source routes
		databaseRoutes.Routes(
			app.Group("/source/database"),
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

	// AI routes
	ai.Routes(app.Group("/v1/api/ai"), params.AIService, appLogger)

	// Main API routes
	api.Routes(app.Group("/v1/api"), params.OlapService, params.AIService, params.DatasetService, appLogger)

	// Project routes
	projectApi.Routes(app.Group("/v1/api/projects"), projectApi.RouterParams{
		Logger:         appLogger,
		ProjectService: params.ProjectService,
		DatasetService: params.DatasetService,
		OlapService:    params.OlapService,
	})

	// Chat routes
	chatApi.Routes(app.Group("/v1/api/chat"), chatApi.RouterParams{
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

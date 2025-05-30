package http

import (
	"log"

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
// @version 1.0
// @description GoPie API documentation
// @host localhost:8000
// @BasePath /
func ServeHttp() error {
	config, err := config.LoadConfig()
	if err != nil {
		log.Fatal("error loading config ", "error-> ", err)
		return err
	}

	logger, err := logger.NewLogger(
		map[string]any{
			"log_level": config.Logger.Level,
			"mode":      config.Logger.Mode,
			"log_file":  config.Logger.LogFile,
		},
	)
	logger.Info("logger initialized")

	// zitadel interceptor setup
	// zitadel.SetupZitadelInterceptor(config, logger)

	source := s3.NewS3SourceRepository(&config.S3, logger)
	olap, err := duckdb.NewOlapDBDriver(&config.OlapDB, logger, &config.S3)
	if err != nil {
		logger.Error("error connecting to motherduck", zap.Error(err))
		return err
	}
	porkeyClient := portkey.NewPortKeyClient(config.PortKey, logger)

	// Store setup
	store := store.NewPostgresStoreRepository(logger)
	err = store.Connect(&config.Postgres)
	if err != nil {
		logger.Error("error connecting to postgres", zap.Error(err))
		return err
	}
	projectStore := projects.NewPostgresProjectStore(store.GetDB(), logger)
	datasetStore := datasets.NewPostgresDatasetStore(store.GetDB(), logger)
	chatStore := chats.NewChatStoreRepository(store.GetDB(), logger)
	dbSourceStore := database_source.NewDatabaseSourceStore(store.GetDB(), logger, config)
	aiAgentRepo := aiagent.NewAIAgent(config.AIAgent.Url, logger)

	olapService := services.NewOlapService(olap, source, logger)
	aiService := services.NewAiDriver(porkeyClient)
	projectService := services.NewProjectService(projectStore)
	datasetService := services.NewDatasetService(datasetStore)
	chatService := services.NewChatService(chatStore, porkeyClient, aiAgentRepo)
	aiAgentService := services.NewAIService(aiAgentRepo)
	dbSourceService := services.NewDatabaseSourceService(dbSourceStore, logger)

	logger.Info("starting server", zap.String("host", config.Server.Host), zap.String("port", config.Server.Port))

	app := fiber.New(fiber.Config{
		CaseSensitive: true,
		AppName:       "gopie",
	})

	app.Use(cors.New(
		cors.Config{
			AllowOrigins:     "http://localhost:3000,https://gopie.factly.dev,https://*.factly.dev",
			AllowMethods:     "GET,POST,HEAD,PUT,DELETE,PATCH,OPTIONS",
			AllowHeaders:     "Origin, Content-Type, Accept, Authorization, X-Requested-With, X-CSRF-Token",
			AllowCredentials: true,
			MaxAge:           86400,
		},
	))
	app.Use(fiberzap.New(fiberzap.Config{
		Logger: logger.Sugar().Desugar(),
	}))

	// Swagger route
	app.Get("/swagger/*", swagger.HandlerDefault)

	// auth route
	api.AuthRoutes(app.Group("/v1/oauth"), logger, config)

	// Only enable authorization if meterus is configured
	if config.Meterus.ApiKey == "" || config.Meterus.Addr == "" {
		logger.Error("meterus config not found")
		logger.Warn("meterus is not configured, authorization will be disabled")
	} else {
		logger.Info("meterus config found")
		client, err := client.NewMeterusClient(config.Meterus.Addr, config.Meterus.ApiKey)
		if err != nil {
			logger.Error("error creating meterus client", zap.Error(err))
			return err
		}
		logger.Info("meterus client created")
		meterus := meterus.NewMeterusApiKeyValidator(client)
		app.Use(middleware.WithApiKeyAuth(meterus, logger))
	}

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status": "ok",
		})
	})

	if config.OlapDB.AccessMode != "read_only" {
		logger.Info("s3 upload routes enabled")
		s3Routes.Routes(app.Group("/source/s3"), olapService, datasetService, projectService, aiAgentService, logger)

		logger.Info("database source routes enabled")
		databaseRoutes.Routes(
			app.Group("/source/database"),
			olapService,
			datasetService,
			projectService,
			aiAgentService,
			dbSourceService,
			logger,
		)
	}

	api.Routes(app.Group("/v1/api"), olapService, aiService, datasetService, logger)
	projectApi.Routes(app.Group("/v1/api/projects"), projectApi.RouterParams{
		Logger:         logger,
		ProjectService: projectService,
		DatasetService: datasetService,
		OlapService:    olapService,
	})
	chatApi.Routes(app.Group("/v1/api/chats"), chatApi.RouterParams{
		Logger:         logger,
		ChatService:    chatService,
		DatasetService: datasetService,
		OlapService:    olapService,
	})

	log.Fatal(app.Listen(":" + config.Server.Port))

	return nil
}

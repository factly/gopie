package http

import (
	"log"

	"github.com/elliot14A/meterus-go/client"
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/meterus"
	"github.com/factly/gopie/infrastructure/motherduck"
	"github.com/factly/gopie/infrastructure/portkey"
	"github.com/factly/gopie/infrastructure/postgres/store"
	"github.com/factly/gopie/infrastructure/postgres/store/datasets"
	"github.com/factly/gopie/infrastructure/postgres/store/projects"
	"github.com/factly/gopie/infrastructure/s3"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/factly/gopie/interfaces/http/routes/api"
	projectApi "github.com/factly/gopie/interfaces/http/routes/api/projects"
	s3Routes "github.com/factly/gopie/interfaces/http/routes/source/s3"
	"github.com/gofiber/contrib/fiberzap"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"go.uber.org/zap"
)

func ServeHttp() error {
	config, err := config.LoadConfig()
	if err != nil {
		log.Fatal("error loading config ", "error-> ", err)
		return err
	}

	logger, err := logger.NewLogger(
		map[string]interface{}{
			"log_level": config.Logger.Level,
			"mode":      config.Logger.Mode,
			"log_file":  config.Logger.LogFile,
		},
	)
	logger.Info("logger initialized")

	source := s3.NewS3SourceRepository(&config.S3, logger)
	olap, err := motherduck.NewMotherDuckOlapoDriver(&config.MotherDuck, logger)
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

	olapService := services.NewOlapService(olap, source, logger)
	aiService := services.NewAiDriver(porkeyClient)
	projectService := services.NewProjectService(projectStore)
	datasetService := services.NewDatasetService(datasetStore)

	logger.Info("starting server", zap.String("host", config.Serve.Host), zap.String("port", config.Serve.Port))

	app := fiber.New(fiber.Config{
		CaseSensitive: true,
		AppName:       "gopie",
	})

	app.Use(cors.New())
	app.Use(fiberzap.New(fiberzap.Config{
		Logger: logger.Sugar().Desugar(),
	}))

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

	if config.MotherDuck.AccessMode != "read_only" {
		logger.Info("s3 upload routes enabled")
		s3Routes.Routes(app.Group("/source/s3"), olapService, datasetService, projectService, logger)
	}

	api.Routes(app.Group("/v1/api"), olapService, aiService, logger)
	projectApi.Routes(app.Group("/v1/api/projects"), projectService, datasetService, logger)

	log.Fatal(app.Listen(":" + config.Serve.Port))

	return nil
}

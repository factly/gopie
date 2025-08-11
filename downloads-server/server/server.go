package server

import (
	"context"
	"fmt"
	"log"

	"github.com/factly/gopie/downlods-server/duckdb"
	"github.com/factly/gopie/downlods-server/pkg/config"
	"github.com/factly/gopie/downlods-server/pkg/logger"
	"github.com/factly/gopie/downlods-server/postgres"
	"github.com/factly/gopie/downlods-server/queue"
	"github.com/factly/gopie/downlods-server/s3"
	"github.com/factly/gopie/downlods-server/server/middleware"
	"github.com/factly/gopie/downlods-server/server/routes"
	"github.com/gofiber/contrib/fiberzap"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"go.uber.org/zap"
)

func ServeHttp() error {
	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatal("error loading config: ", err)
		return err
	}

	logger, err := logger.NewLogger(
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
	logger.Info("config loaded successfully")
	logger.Info("logger initialized")

	s3 := s3.NewS3ObjectStore(cfg.S3, logger)
	err = s3.Connect(context.Background())
	if err != nil {
		logger.Error("Error connecting to s3 ", zap.Error(err))
	}

	dbStore := postgres.NewPostgresStore(logger)
	err = dbStore.Connect(&cfg.Postgres)
	if err != nil {
		logger.Error("Error connecting to postgres", zap.Error(err))
		return err
	}
	olapStore, err := duckdb.NewMotherDuckDriver(&cfg.OlapDB, logger)
	if err != nil {
		logger.Error("Error initializing olapStore", zap.Error(err))
		return err
	}

	manager := queue.NewSubscriptionManager(logger)
	queue := queue.NewDownloadQueue(dbStore, olapStore, s3, logger, manager, &cfg.Queue)

	go queue.Start()

	app := fiber.New(fiber.Config{
		CaseSensitive: true,
		AppName:       "gopie-downloads-server",
	})

	app.Use(cors.New(cors.Config{
		AllowOrigins:     "http://localhost:3000,https://gopie.factly.dev,https://*.factly.dev",
		AllowMethods:     "GET,POST,HEAD,PUT,DELETE,PATCH,OPTIONS",
		AllowHeaders:     "Origin, Content-Type, Accept, Authorization, X-Requested-With, X-CSRF-Token, userID, x-user-id, x-project-ids, x-dataset-ids, x-chat-id, x-organization-id",
		AllowCredentials: true,
		MaxAge:           86400,
	}))

	app.Use(fiberzap.New(fiberzap.Config{
		Logger: logger.Logger,
	}))

	handler := routes.NewHttpHandler(logger, queue)

	// Register public routes (no auth required)
	handler.RegisterPublicRoutes(app)

	// Apply auth middleware for protected routes
	app.Use(middleware.AuthorizeHeaders(logger))

	// Register protected routes
	handler.RegisterProtectedRoutes(app)
	addr := fmt.Sprintf("%s:%s", cfg.Server.Host, cfg.Server.Port)

	if err := app.Listen(addr); err != nil {
		logger.Fatal("Error starting server", zap.Error(err))
		return err
	}

	return nil
}

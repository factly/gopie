package http

import (
	"log"

	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/motherduck"
	"github.com/factly/gopie/infrastructure/portkey"
	"github.com/factly/gopie/infrastructure/s3"
	"github.com/factly/gopie/interfaces/http/routes/api"
	s3Routes "github.com/factly/gopie/interfaces/http/routes/source/s3"
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

	service := services.NewDriver(olap, nil, source, logger)
	aiService := services.NewAiDriver(porkeyClient)

	logger.Info("starting server", zap.String("host", config.Serve.Host), zap.String("port", config.Serve.Port))

	app := fiber.New(fiber.Config{
		CaseSensitive: true,
		StrictRouting: true,
		AppName:       "gopie",
	})

	app.Use(cors.New())

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status": "ok",
		})
	})

	s3Routes.Routes(app.Group("/source/s3"), service, logger)
	api.Routes(app.Group("/api"), service, aiService, logger)

	log.Fatal(app.Listen(":" + config.Serve.Port))

	return nil
}

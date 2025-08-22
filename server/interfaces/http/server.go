package http

import (
	"context"
	"log"
	"sync"

	"github.com/factly/gopie/application/services"
	_ "github.com/factly/gopie/docs" // Import generated Swagger docs
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/aiagent"
	"github.com/factly/gopie/infrastructure/duckdb"
	"github.com/factly/gopie/infrastructure/openai"
	"github.com/factly/gopie/infrastructure/postgres/store"
	"github.com/factly/gopie/infrastructure/postgres/store/chats"
	"github.com/factly/gopie/infrastructure/postgres/store/database_source"
	"github.com/factly/gopie/infrastructure/postgres/store/datasets"
	"github.com/factly/gopie/infrastructure/postgres/store/downloads"
	"github.com/factly/gopie/infrastructure/postgres/store/projects"
	"github.com/factly/gopie/infrastructure/s3"
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
	appLogger.Info("logger initialized")

	// Initialize repositories and services
	olap, err := duckdb.NewOlapDBDriver(&cfg.OlapDB, appLogger, &cfg.S3)
	if err != nil {
		appLogger.Error("error connecting to olap database", zap.Error(err))
		return err
	}

	openaiClient := openai.NewOpenAIClient(cfg.OpenAI, appLogger)

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
	downloadsStore := downloads.NewPostgresDownloadsStore(storeRepo.GetDB(), appLogger)
	s3Repo := s3.NewS3ObjectStore(cfg.S3, cfg.DownloadsServer.Bucket, appLogger)
	aiAgentRepo := aiagent.NewAIAgent(cfg.AIAgent.Url, appLogger)

	olapService := services.NewOlapService(olap, appLogger)
	// Initialize services
	aiService := services.NewAiDriver(openaiClient)
	projectService := services.NewProjectService(projectStore)
	datasetService := services.NewDatasetService(datasetStore)
	chatService := services.NewChatService(chatStore, openaiClient, aiAgentRepo)
	aiAgentService := services.NewAIService(aiAgentRepo)
	dbSourceService := services.NewDatabaseSourceService(dbSourceStore, appLogger)
	downloadService, err := services.NewDownloadsService(services.DownloadsServiceParams{
		Cfg:    cfg.DownloadsServer,
		Store:  downloadsStore,
		S3:     s3Repo,
		Olap:   olap,
		Logger: appLogger,
	})
	if err != nil {
		appLogger.Fatal("error initializing downloads service", zap.Error(err))
		return err
	}

	// Create ServerParams to pass to both servers
	params := &ServerParams{
		Logger:           appLogger,
		OlapService:      olapService,
		AIService:        aiService,
		ProjectService:   projectService,
		DatasetService:   datasetService,
		ChatService:      chatService,
		AIAgentService:   aiAgentService,
		DbSourceService:  dbSourceService,
		DownloadsService: downloadService,
	}

	var wg sync.WaitGroup

	// Create a wait group to wait for both servers to shut down
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	wg.Add(2)

	go func() {
		defer wg.Done()
		appLogger.Info("Web Application server is enabled via config. Starting in a goroutine...")
		if err := serve(cfg, params, ctx); err != nil {
			appLogger.Error("Web Application server failed to start", zap.Error(err))
			cancel()
		}
	}()

	go func() {
		defer wg.Done()
		appLogger.Info("Internal server is enabled via config. Starting in a goroutine...")
		if err := serveInternal(cfg, params, ctx); err != nil {
			appLogger.Error("Web Application server failed to start", zap.Error(err))
			cancel()
		}
	}()

	wg.Wait()
	appLogger.Info("All servers have shut down gracefully.")
	return nil
}

package http

import (
	"context"
	"fmt"
	"log"
	"sync"

	"github.com/factly/gopie/application/services"
	_ "github.com/factly/gopie/docs" // Import generated Swagger docs
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/aiagent"
	"github.com/factly/gopie/infrastructure/duckdb"
	"github.com/factly/gopie/infrastructure/portkey"
	"github.com/factly/gopie/infrastructure/postgres/store"
	"github.com/factly/gopie/infrastructure/postgres/store/chats"
	"github.com/factly/gopie/infrastructure/postgres/store/database_source"
	"github.com/factly/gopie/infrastructure/postgres/store/datasets"
	"github.com/factly/gopie/infrastructure/postgres/store/projects"
	"github.com/factly/gopie/infrastructure/s3"
	"go.uber.org/zap"
)

// contains checks if a string is present in a slice of strings.
func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

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
	appLogger.Info("logger initialized")

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

	// Determine which servers to start based on config
	runWebAppServer := contains(cfg.EnabledServers, "webapp")
	runApiServer := contains(cfg.EnabledServers, "api")

	if !runWebAppServer && !runApiServer {
		errMsg := "No servers enabled to start. Check GOPIE_ENABLED_SERVERS. Valid options: 'api', 'webapp'."
		appLogger.Error(errMsg)
		return fmt.Errorf("%s", errMsg)
	}

	if runWebAppServer {
		appLogger.Info("Web Application server is enabled via config. Starting in a goroutine...")
		wg.Add(1)
		go func() {
			defer wg.Done()
			if err := serveWebApp(cfg, params, ctx); err != nil {
				appLogger.Error("Web Application server failed to start", zap.Error(err))
				cancel()
			}
		}()
	} else {
		appLogger.Info("Web Application server is disabled via config.")
	}

	if runApiServer {
		appLogger.Info("API server is enabled via config. Starting...")
		if err := serveApiServer(cfg, params); err != nil {
			appLogger.Error("API server failed to start", zap.Error(err))
			cancel()
			return err
		}
	} else {
		appLogger.Info("API server is disabled via config. Main goroutine will wait for other active servers if any.")
	}

	// Wait for both servers to shut down
	wg.Wait()
	return nil
}

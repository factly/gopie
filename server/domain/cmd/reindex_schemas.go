package cmd

import (
	"log"
	"sync"

	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/aiagent"
	"github.com/factly/gopie/infrastructure/postgres/store"
	"github.com/factly/gopie/infrastructure/postgres/store/datasets"
	"github.com/factly/gopie/infrastructure/postgres/store/projects"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"go.uber.org/zap"
)

func init() {
	rootCmd.AddCommand(reindexSchemasCmd)
}

var reindexSchemasCmd = &cobra.Command{
	Use:   "reindex-schemas",
	Short: "Re-indexes all project and dataset schemas and uploads them to the AI agent.",
	Run: func(cmd *cobra.Command, args []string) {
		viper.AutomaticEnv()
		appLogger, err := logger.NewLogger(nil)
		if err != nil {
			log.Fatal(err)
		}

		// Store setup
		storeRepo := store.NewPostgresStoreRepository(appLogger)
		err = storeRepo.Connect(&config.PostgresConfig{
			Host:     viper.GetString("GOPIE_POSTGRES_HOST"),
			Port:     viper.GetString("GOPIE_POSTGRES_PORT"),
			Database: viper.GetString("GOPIE_POSTGRES_DB"),
			User:     viper.GetString("GOPIE_POSTGRES_USER"),
			Password: viper.GetString("GOPIE_POSTGRES_PASSWORD"),
		})
		if err != nil {
			appLogger.Error("error connecting to postgres", zap.Error(err))
			return
		}
		defer storeRepo.Close()

		// Initialize repositories
		projectStore := projects.NewPostgresProjectStore(storeRepo.GetDB(), appLogger)
		datasetStore := datasets.NewPostgresDatasetStore(storeRepo.GetDB(), appLogger)
		aiAgentRepo := aiagent.NewAIAgent(viper.GetString("GOPIE_AI_AGENT_URL"), appLogger)

		// Initialize services
		projectService := services.NewProjectService(projectStore)
		datasetService := services.NewDatasetService(datasetStore)

		appLogger.Info("Re-indexing schemas...")

		// Get all projects
		projects, err := projectService.ListAllProjects()
		if err != nil {
			appLogger.Fatal("failed to list projects", zap.Error(err))
		}

		const numWorkers = 10

		// Iterate over each project
		for _, project := range projects {
			appLogger.Info("Processing project...", zap.String("project", project.ID))

			// Create a buffered channel for jobs
			jobs := make(chan *models.Dataset, numWorkers*2) // Buffer for 2 batches per worker
			var wg sync.WaitGroup

			// Start the worker pool with a fixed number of workers
			for i := range numWorkers {
				wg.Add(1)
				go func(workerID int) {
					defer wg.Done()
					for dataset := range jobs {
						appLogger.Info("Indexing dataset...", zap.Int("workerID", workerID), zap.String("datasetID", dataset.ID))

						err := aiAgentRepo.UploadSchema(&models.SchemaParams{
							ProjectID: project.ID,
							DatasetID: dataset.ID,
						})
						if err != nil {
							appLogger.Error("failed to upload schema for dataset",
								zap.String("project_id", project.ID),
								zap.String("dataset_id", dataset.ID),
								zap.Int("worker_id", workerID),
								zap.Error(err))
						} else {
							appLogger.Info("Successfully uploaded schema for dataset", zap.Int("workerID", workerID), zap.String("datasetID", dataset.ID))
						}
					}
				}(i + 1)
			}

			// Fetch datasets in batches and send them directly to workers
			datasetsLoaded := 0
			limit := 10
			page := 1

			for {
				datasets, err := datasetService.List(project.ID, limit, page)
				if err != nil {
					appLogger.Error("failed to list datasets for project",
						zap.String("project_id", project.ID),
						zap.Int("page", page),
						zap.Error(err))
					break
				}

				appLogger.Info("loaded datasets successfully",
					zap.Int("length", len(datasets.Results)),
					zap.Int("page", page))

				batchSize := len(datasets.Results)
				if batchSize == 0 {
					break
				}

				datasetsLoaded += batchSize

				for _, dataset := range datasets.Results {
					jobs <- dataset
				}

				page++
			}

			appLogger.Info("Dispatched datasets to workers", zap.Int("datasetsLoaded", datasetsLoaded), zap.String("projectID", project.ID))

			close(jobs)
			wg.Wait()
			appLogger.Info("Finished processing project", zap.String("projectID", project.ID))
		}

		appLogger.Info("Schema re-indexing complete.")
	},
}

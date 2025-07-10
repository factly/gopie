package cmd

import (
	"fmt"
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
	"go.uber.org/zap"
)

func init() {
	rootCmd.AddCommand(reindexSchemasCmd)
}

var reindexSchemasCmd = &cobra.Command{
	Use:   "reindex-schemas",
	Short: "Re-indexes all project and dataset schemas and uploads them to the AI agent.",
	Run: func(cmd *cobra.Command, args []string) {
		cfg, err := config.LoadConfig()
		if err != nil {
			log.Fatal(err)
		}

		// Initialize logger
		appLogger, err := logger.NewLogger(map[string]any{
			"log_level": cfg.Logger.Level,
			"mode":      cfg.Logger.Mode,
			"log_file":  cfg.Logger.LogFile,
		})
		if err != nil {
			log.Fatal(err)
		}

		// Store setup
		storeRepo := store.NewPostgresStoreRepository(appLogger)
		err = storeRepo.Connect(&cfg.Postgres)
		if err != nil {
			appLogger.Error("error connecting to postgres", zap.Error(err))
			return
		}
		defer storeRepo.Close()

		// Initialize repositories
		projectStore := projects.NewPostgresProjectStore(storeRepo.GetDB(), appLogger)
		datasetStore := datasets.NewPostgresDatasetStore(storeRepo.GetDB(), appLogger)
		aiAgentRepo := aiagent.NewAIAgent(cfg.AIAgent.Url, appLogger)

		// Initialize services
		projectService := services.NewProjectService(projectStore)
		datasetService := services.NewDatasetService(datasetStore)

		fmt.Println("Re-indexing schemas...")

		// Get all projects
		projects, err := projectService.ListAllProjects()
		if err != nil {
			appLogger.Fatal("failed to list projects", zap.Error(err))
		}

		// Iterate over each project
		for _, project := range projects {
			var wg sync.WaitGroup
			limit := 10
			offset := 0

			for {
				// Get a batch of datasets for the current project
				datasets, err := datasetService.List(project.ID, limit, offset)
				if err != nil {
					appLogger.Error("failed to list datasets for project", zap.String("project_id", project.ID), zap.Error(err))
					break // Break on error to move to the next project
				}

				if len(datasets.Results) == 0 {
					// No more datasets for this project
					break
				}

				// Iterate over each dataset in the batch and upload schema concurrently
				for _, dataset := range datasets.Results {
					wg.Add(1)
					go func(d *models.Dataset) {
						defer wg.Done()
						// Upload the schema to the AI agent
						err := aiAgentRepo.UploadSchema(&models.UploadSchemaParams{
							ProjectID: project.ID,
							DatasetID: d.ID,
						})
						if err != nil {
							appLogger.Error("failed to upload schema for dataset", zap.String("dataset_id", d.ID), zap.Error(err))
						} else {
							fmt.Printf("Successfully uploaded schema for dataset %s in project %s\n", d.ID, project.ID)
						}
					}(dataset) // Pass the dataset pointer to the goroutine
				}

				offset += limit
			}
			// Wait for all uploads for the current project to complete
			wg.Wait()
		}

		fmt.Println("Schema re-indexing complete.")
	},
}

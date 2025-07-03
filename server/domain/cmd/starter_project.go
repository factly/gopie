package cmd

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/factly/gopie/infrastructure/aiagent"
	"github.com/factly/gopie/infrastructure/duckdb"
	"github.com/factly/gopie/infrastructure/postgres/store"
	"github.com/factly/gopie/infrastructure/postgres/store/datasets"
	"github.com/factly/gopie/infrastructure/postgres/store/projects"
	"github.com/factly/gopie/infrastructure/s3"
	"github.com/spf13/cobra"
	"go.uber.org/zap"
)

func init() {
	rootCmd.AddCommand(starterProjectCmd)
}

var starterProjectCmd = &cobra.Command{
	Use:   "starter-project",
	Short: "Create a starter project",
	Run: func(cmd *cobra.Command, args []string) {
		if err := setupStarterProject(); err != nil {
			log.Fatal("error setting up starter project: ", err)
		}
	},
}

func setupStarterProject() error {
	cfg, err := config.LoadConfig()
	if err != nil {
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

	source := s3.NewS3SourceRepository(&cfg.S3, appLogger)
	olap, err := duckdb.NewOlapDBDriver(&cfg.OlapDB, appLogger, &cfg.S3)
	if err != nil {
		appLogger.Error("error connecting to olap database", zap.Error(err))
		return err
	}

	storeRepo := store.NewPostgresStoreRepository(appLogger)
	err = storeRepo.Connect(&cfg.Postgres)
	if err != nil {
		appLogger.Error("error connecting to postgres", zap.Error(err))
		return err
	}

	projectStore := projects.NewPostgresProjectStore(storeRepo.GetDB(), appLogger)
	datasetStore := datasets.NewPostgresDatasetStore(storeRepo.GetDB(), appLogger)

	aiAgentRepo := aiagent.NewAIAgent(cfg.AIAgent.Url, appLogger)

	olapService := services.NewOlapService(olap, source, appLogger)

	uploadedFiles, err := uploadDatasetFilesToMinio(appLogger, source)
	if err != nil {
		appLogger.Error("error uploading dataset files to MinIO", zap.Error(err))
		return err
	}

	project, err := projectStore.Create(context.Background(), models.CreateProjectParams{
		Name:        "Starter Project",
		Description: "This is a starter project created by the starter-project command.",
		CreatedBy:   "system",
	})
	if err != nil {
		appLogger.Error("error creating starter project", zap.Error(err))
		return err
	}

	appLogger.Info("Starter project created successfully", zap.String("project_id", project.ID))

	// Process files sequentially
	for _, filePath := range uploadedFiles {
		olapTableName := fmt.Sprintf("gp_%s", pkg.RandomString(13))
		olapTable, err := olapService.IngestS3File(context.Background(), filePath, olapTableName, nil)
		if err != nil {
			appLogger.Error("error ingesting file to OLAP", zap.String("file_path", filePath), zap.Error(err))
			return err
		}

		appLogger.Info("File ingested to OLAP successfully",
			zap.String("file_path", filePath),
			zap.String("olap_table", olapTable.TableName))

		count, columns, err := getMetrics(olapTable.TableName, olapService, appLogger)
		if err != nil {
			appLogger.Error("Error fetching dataset metrics", zap.Error(err), zap.String("table_name", olapTable.TableName))
			// Clean up the created OLAP table since metrics fetch failed
			dropErr := olapService.DropTable(olapTable.TableName)
			if dropErr != nil {
				appLogger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", olapTable.TableName))
			}
			return err
		}

		// Create a dataset for the ingested file
		dataset, err := datasetStore.Create(context.Background(), &models.CreateDatasetParams{
			Name:        fmt.Sprintf(olapTable.TableName),
			Description: fmt.Sprintf("Dataset created for the file %s", filePath),
			ProjectID:   project.ID,
			CreatedBy:   "system",
			UpdatedBy:   "system",
			Columns:     columns,
			FilePath:    filePath,
			Size:        olapTable.Size,
			RowCount:    count,
		})
		if err != nil {
			appLogger.Error("Error creating dataset record", zap.Error(err))
			dropErr := olapService.DropTable(olapTable.TableName)
			if dropErr != nil {
				appLogger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", olapTable.TableName))
			}
			return err
		}

		appLogger.Info("Dataset created successfully",
			zap.String("dataset_id", dataset.ID),
			zap.String("dataset_name", dataset.Name),
			zap.String("olap_table", olapTable.TableName),
			zap.Int("row_count", count),
			zap.Int("column_count", len(columns)))

		datasetSummary, err := olapService.GetDatasetSummary(olapTable.TableName)
		if err != nil {
			appLogger.Error("Error fetching dataset summary", zap.Error(err))
			// Clean up the dataset record and OLAP table since dataset summary fetch failed
			deleteErr := datasetStore.Delete(context.Background(), dataset.ID, dataset.OrgID)
			if deleteErr != nil {
				appLogger.Error("Failed to delete dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", dataset.ID))
			}
			dropErr := olapService.DropTable(olapTable.TableName)
			if dropErr != nil {
				appLogger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", olapTable.TableName))
			}
			return err
		}

		if datasetSummary != nil {
			summaryMap := make(map[string]int)
			for i := range *datasetSummary {
				summaryMap[(*datasetSummary)[i].ColumnName] = i
			}
		}

		_, err = datasetStore.CreateDatasetSummary(context.Background(), olapTable.TableName, datasetSummary)
		if err != nil {
			appLogger.Error("Error creating dataset summary", zap.Error(err), zap.String("table_name", olapTable.TableName))
			// Clean up the dataset record and OLAP table since summary creation failed
			deleteErr := datasetStore.Delete(context.Background(), dataset.ID, dataset.OrgID)
			if deleteErr != nil {
				appLogger.Error("Failed to delete dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", dataset.ID))
			}
			dropErr := olapService.DropTable(olapTable.TableName)
			if dropErr != nil {
				appLogger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", olapTable.TableName))
			}
			return err
		}

		appLogger.Info("Dataset summary created successfully",
			zap.String("dataset_id", dataset.ID),
			zap.String("olap_table", olapTable.TableName),
			zap.Int("row_count", count),
			zap.Int("column_count", len(columns)))

		err = aiAgentRepo.UploadSchema(&models.UploadSchemaParams{
			ProjectID: project.ID,
			DatasetID: dataset.ID,
		})
		if err != nil {
			appLogger.Error("Error uploading schema to AI Agent", zap.Error(err), zap.String("dataset_id", dataset.ID))
			// Clean up the dataset record and OLAP table since schema upload failed
			deleteErr := datasetStore.Delete(context.Background(), dataset.ID, dataset.OrgID)
			if deleteErr != nil {
				appLogger.Error("Failed to delete dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", dataset.ID))
			}
			dropErr := olapService.DropTable(olapTable.TableName)
			if dropErr != nil {
				appLogger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", olapTable.TableName))
			}
			deleteSErr := datasetStore.DeleteDatasetSummary(context.Background(), olapTable.TableName)
			if deleteSErr != nil {
				appLogger.Error("Failed to delete dataset summary during cleanup", zap.Error(deleteSErr), zap.String("table_name", olapTable.TableName))
			}
			return err
		}

		appLogger.Info("Schema uploaded to AI Agent successfully",
			zap.String("dataset_id", dataset.ID),
			zap.String("file_path", filePath),
		)

		appLogger.Info("Dataset upload complete",
			zap.String("dataset_id", dataset.ID),
			zap.String("file_path", filePath),
		)
	}

	appLogger.Info("All files processed successfully", zap.Int("file_count", len(uploadedFiles)))
	return nil
}

func uploadDatasetFilesToMinio(logger *logger.Logger, s3Source repositories.SourceRepository) ([]string, error) {
	datasetFilesPath := os.Getenv("GOPIE_DATASET_FILES_PATH")
	bucketName := "gopie"
	if datasetFilesPath == "" {
		logger.Warn("GOPIE_DATASET_FILES_PATH environment variable is not set")
		logger.Info("Using default path: ./starter-project-datasets/")
		datasetFilesPath = "./starter-project-datasets/"
	}

	listAllFiles, err := os.ReadDir(datasetFilesPath)
	if err != nil {
		logger.Error("error reading dataset files directory", zap.Error(err), zap.String("path", datasetFilesPath))
		return nil, err
	}

	// Count only non-directory files
	fileCount := 0
	for _, file := range listAllFiles {
		if !file.IsDir() {
			fileCount++
		}
	}

	logger.Info("Starting file upload process", zap.Int("total_files", fileCount))

	uploadedFiles := make([]string, 0, fileCount)

	// Process files sequentially
	for i, file := range listAllFiles {
		if file.IsDir() {
			continue
		}

		filePath := datasetFilesPath + file.Name()
		logger.Info("Uploading file",
			zap.String("file_name", file.Name()),
			zap.String("file_path", filePath),
			zap.Int("file_number", i+1),
			zap.Int("total_files", fileCount))

		start := time.Now()
		location, err := s3Source.UploadFile(context.Background(), bucketName, filePath)
		duration := time.Since(start)

		if err != nil {
			logger.Error("Failed to upload file",
				zap.String("file_path", filePath),
				zap.Duration("duration", duration),
				zap.Error(err))
			return nil, err
		}

		s3Path := fmt.Sprintf("s3://%s/%s", bucketName, file.Name())
		logger.Info("File uploaded successfully",
			zap.String("file_path", filePath),
			zap.String("s3_path", s3Path),
			zap.String("location", location),
			zap.Duration("duration", duration))

		uploadedFiles = append(uploadedFiles, s3Path)
	}

	logger.Info("All files uploaded successfully",
		zap.Int("file_count", len(uploadedFiles)),
		zap.String("bucket", bucketName))
	return uploadedFiles, nil
}

func getMetrics(tableName string, olapSvc *services.OlapService, logger *logger.Logger) (int, []map[string]any, error) {
	// Get row count
	countSql := "select count(*) from " + tableName
	countResult, err := olapSvc.ExecuteQuery(countSql)
	if err != nil {
		return 0, nil, err
	}

	count, ok := countResult[0]["count_star()"].(int64)
	if !ok {
		logger.Error("Invalid count result type", zap.Any("count_result", countResult[0]["count_star()"]))
		return 0, nil, fmt.Errorf("Invalid count result type")
	}

	// Get column descriptions
	columns, err := olapSvc.ExecuteQuery("desc " + tableName)
	if err != nil {
		return 0, nil, err
	}

	return int(count), columns, nil
}

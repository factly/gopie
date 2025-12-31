package database

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// resourceCleanup defines what resources need to be cleaned up in case of an error
// This is similar to the implementation in s3/create.go
// (tableName, datasetID, orgID, sourceID, booleans for dataset, summary, source)
type resourceCleanup struct {
	tableName  string
	datasetID  string
	orgID      string
	sourceID   string
	hasDataset bool
	hasSummary bool
	hasSource  bool
}

// cleanupResources handles cleanup of created resources in case of errors
func (h *httpHandler) cleanupResources(rc resourceCleanup) {
	// Delete dataset summary if it was created
	if rc.hasSummary {
		summaryErr := h.datasetSvc.DeleteDatasetSummary(rc.tableName)
		if summaryErr != nil {
			h.logger.Error("Failed to delete dataset summary during cleanup", zap.Error(summaryErr), zap.String("dataset_name", rc.tableName))
		}
	}

	// Delete dataset record if it was created
	if rc.hasDataset {
		deleteErr := h.datasetSvc.Delete(rc.datasetID, rc.orgID)
		if deleteErr != nil {
			h.logger.Error("Failed to delete dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", rc.datasetID))
		}
	}

	// Delete database source record if it was created
	if rc.hasSource {
		deleteSErr := h.dbSourceSvc.Delete(rc.sourceID)
		if deleteSErr != nil {
			h.logger.Error("Failed to delete database source during cleanup", zap.Error(deleteSErr), zap.String("source_id", rc.sourceID))
		}
	}

	// Always try to drop the OLAP table if tableName is provided
	if rc.tableName != "" {
		dropErr := h.olapSvc.DropTable(rc.tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", rc.tableName))
		}
	}
}

// createRequestBody represents the request body for creating a database source
// @Description Request body for creating a database source dataset
type createRequestBody struct {
	// Driver of the database
	Driver string `json:"driver" validate:"required,oneof=postgres mysql" example:"postgres"`
	// Connection string for the Postgres database
	ConnectionString string `json:"connection_string" validate:"required" example:"postgres://username:password@localhost:5432/database"`
	// SQL query to execute
	SQLQuery string `json:"sql_query" validate:"required" example:"SELECT * FROM users"`
	// Timestamp column for incremental updates
	TimestampColumn string `json:"timestamp_column" validate:"omitempty,min=1" example:"updated_at"`
	// Description of the dataset
	Description string `json:"description,omitempty" validate:"omitempty,min=10,max=1000" example:"User data from our production database"`
	// ID of the project to add the dataset to
	ProjectID string `json:"project_id" validate:"required,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	// User ID of the creator
	CreatedBy string `json:"created_by" validate:"required" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Alias of the dataset
	Alias        string `json:"alias" validate:"required,min=3" example:"users_data"`
	CustomPrompt string `json:"custom_prompt"`
	// Maximum number of tokens to generate (optional)
	MaxTokens *int `json:"maxTokens,omitempty" example:"1000"`
}

// @Summary Create dataset from Postgres
// @Description Create a new dataset from a Postgres database query
// @Tags database
// @Accept json
// @Produce json
// @Param body body createRequestBody true "Create request parameters"
// @Success 201 {object} responses.SuccessResponse{data=map[string]interface{}{"dataset":models.Dataset,"summary":any}}
// @Failure 400 {object} responses.ErrorResponse "Invalid request body or database connection error"
// @Failure 404 {object} responses.ErrorResponse "Project not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /source/database/upload [post]
func (h *httpHandler) create(ctx *fiber.Ctx) error {
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)
	userID := ctx.Locals(middleware.UserCtxKey).(string)

	// Get request body from context
	var body createRequestBody
	if err := ctx.BodyParser(&body); err != nil {
		h.logger.Info("Error parsing request body", zap.Error(err))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body format",
			"code":    fiber.StatusBadRequest,
		})
	}

	err := pkg.ValidateRequest(h.logger, &body)
	if err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}

	// Check if project exists
	project, err := h.projectSvc.Details(body.ProjectID, orgID)
	if err != nil {
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			h.logger.Error("Project not found", zap.Error(err), zap.String("project_id", body.ProjectID))
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Project not found",
				"message": fmt.Sprintf("Project with ID %s not found", body.ProjectID),
				"code":    fiber.StatusNotFound,
			})
		}
		h.logger.Error("Error fetching project", zap.Error(err), zap.String("project_id", body.ProjectID))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error validating project",
			"code":    fiber.StatusInternalServerError,
		})
	}

	h.logger.Info("Creating database source dataset", zap.String("project_id", project.ID))

	tableName := fmt.Sprintf("gp_%s", pkg.RandomString(13))

	if body.Driver == "postgres" {
		err := h.olapSvc.CreateTableFromPostgres(body.ConnectionString, body.SQLQuery, tableName)
		if err != nil {
			h.logger.Error("Error creating table from postgres", zap.Error(err))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error creating table from postgres",
				"code":    fiber.StatusInternalServerError,
			})
		}
	} else {
		err := h.olapSvc.CreateTableFromMySql(body.ConnectionString, body.SQLQuery, tableName)
		if err != nil {
			h.logger.Error("Error creating table from mysql", zap.Error(err))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error creating table from mysql",
				"code":    fiber.StatusInternalServerError,
			})
		}
	}

	// Create the database source

	time.Sleep(2 * time.Second) // Wait for the table to be created in OLAP

	cleanup := resourceCleanup{
		tableName: tableName,
	}

	count, columns, err := h.getMetrics(tableName)
	if err != nil {
		h.logger.Error("Error fetching dataset metrics", zap.Error(err), zap.String("table_name", tableName))
		h.cleanupResources(cleanup)
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset metrics",
			"code":    fiber.StatusInternalServerError,
		})
	}

	datasetSummary, err := h.olapSvc.GetDatasetSummary(tableName)
	if err != nil {
		h.logger.Error("Error fetching dataset summary", zap.Error(err))
		h.cleanupResources(cleanup)
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	summaryBytes, _ := json.Marshal(datasetSummary)
	summaryString := string(summaryBytes)
	cleanup.hasSummary = true
	rows, err := h.olapSvc.ExecuteQuery(fmt.Sprintf("select * from %s order by random() limit 50", tableName))
	if err != nil {
		h.logger.Error("Error fetching sample rows", zap.Error(err))
		h.cleanupResources(cleanup)
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching sample rows",
			"code":    fiber.StatusInternalServerError,
		})
	}

	rowsBytes, _ := json.Marshal(rows)
	rowsString := string(rowsBytes)

	descriptions, err := h.aiSvc.GenerateColumnDescriptions(rowsString, summaryString, body.MaxTokens)
	if err != nil {
		h.logger.Error("Error generating column descriptions", zap.Error(err))
		h.cleanupResources(cleanup)
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset metrics",
			"code":    fiber.StatusInternalServerError,
		})
	}

	columnNames := make([]string, 0, len(*datasetSummary))

	if descriptions != nil {
		for i := range *datasetSummary {
			columnNames = append(columnNames, (*datasetSummary)[i].ColumnName)
			(*datasetSummary)[i].Description = descriptions[(*datasetSummary)[i].ColumnName]
		}
	}

	datasetDesciption, err := h.aiSvc.GenerateDatasetDescription(
		body.Alias,
		columnNames,
		descriptions,
		rowsString,
		summaryString,
		body.MaxTokens,
	)
	if err != nil {
		h.logger.Error("Error generating dataset description", zap.Error(err))
		h.cleanupResources(cleanup)
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to generate dataset description")
	}
	// override the description provided by user for now
	body.Description = datasetDesciption

	dataset, err := h.datasetSvc.Create(&models.CreateDatasetParams{
		Name:         tableName,
		Description:  body.Description,
		ProjectID:    project.ID,
		Columns:      columns,
		RowCount:     count,
		Source:       "database",
		Alias:        body.Alias,
		CreatedBy:    userID,
		UpdatedBy:    userID,
		OrgID:        orgID,
		CustomPrompt: body.CustomPrompt,
	})
	if err != nil {
		h.logger.Error("Error creating dataset record", zap.Error(err))
		h.cleanupResources(cleanup)
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset record",
			"code":    fiber.StatusInternalServerError,
		})
	}
	cleanup.hasDataset = true
	cleanup.datasetID = dataset.ID
	cleanup.orgID = dataset.OrgID

	var lastUpdateAt string

	if body.TimestampColumn == "" {
		lastUpdateAt = ""
	} else {
		t, err := h.olapSvc.GetLatestTimestamp(tableName, body.TimestampColumn)
		if err != nil {
			h.logger.Error("Error fetching latest timestamp", zap.Error(err))
			h.cleanupResources(cleanup)
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error fetching latest timestamp",
				"code":    fiber.StatusInternalServerError,
			})
		}
		if t != nil {
			lastUpdateAt = *t
		}
	}

	dbSourceParams := &models.CreateDatabaseSourceParams{
		ConnectionString: body.ConnectionString,
		SQLQuery:         body.SQLQuery,
		OrganizationID:   orgID,
		TimestampColumn:  body.TimestampColumn,
		DatasetID:        dataset.ID,
		LastUpdatedAt:    lastUpdateAt,
		Driver:           body.Driver,
	}

	source, err := h.dbSourceSvc.Create(dbSourceParams)
	if err != nil {
		h.logger.Error("Error creating database source", zap.Error(err))
		h.cleanupResources(cleanup)
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating database source",
			"code":    fiber.StatusInternalServerError,
		})
	}
	cleanup.hasSource = true
	cleanup.sourceID = source.ID

	summary, err := h.datasetSvc.CreateDatasetSummary(tableName, datasetSummary)
	if err != nil {
		h.logger.Error("Error creating dataset summary", zap.Error(err))
		cleanup.hasSummary = true
		h.cleanupResources(cleanup)
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}
	cleanup.hasSummary = true

	err = h.aiAgentSvc.UploadSchema(&models.SchemaParams{
		DatasetID: dataset.ID,
		ProjectID: project.ID,
	})
	if err != nil {
		h.logger.Error("Error uploading schema to AI agent", zap.Error(err))
		h.cleanupResources(cleanup)
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error uploading schema to AI agent",
			"code":    fiber.StatusInternalServerError,
		})
	}

	h.logger.Info("Database source dataset creation completed successfully",
		zap.String("dataset_id", dataset.ID),
		zap.String("project_id", project.ID),
		zap.String("table_name", tableName))

	return ctx.Status(fiber.StatusCreated).JSON(fiber.Map{
		"data": map[string]any{
			"dataset": dataset,
			"summary": summary,
		},
	})
}

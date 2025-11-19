package database

import (
	"fmt"
	"strings"
	"time"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type refreshRequestBody struct {
	ProjectID   string `json:"project_id" validate:"required,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	DatasetName string `json:"dataset_name" validate:"required,min=3" example:"gp_asdfghjklqwerty"`
	RefreshType string `json:"refresh_type" validate:"required,oneof=full incremental" example:"full"`
}

// @Summary Update dataset from database source
// @Description Updates an existing dataset from a database source by re-executing the source query and refreshing metrics, columns, row count, summary, and schema embedding
// @Tags database
// @Accept json
// @Produce json
// @Param body body updateRequestBody true "Update request parameters"
// @Success 201 {object} responses.SuccessResponse{data=models.Dataset}
// @Failure 400 {object} responses.ErrorResponse "Invalid request body or database connection error"
// @Failure 404 {object} responses.ErrorResponse "Project or dataset not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /source/database/refresh [post]
func (h *httpHandler) refresh(ctx *fiber.Ctx) error {
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)
	userID := ctx.Locals(middleware.UserCtxKey).(string)

	// Get request body from context
	var body refreshRequestBody
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

	d, err := h.datasetSvc.GetByTableName(body.DatasetName, orgID)
	if err != nil {
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			h.logger.Error("Dataset not found", zap.Error(err), zap.String("dataset_id", body.DatasetName))
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Dataset not found",
				"message": fmt.Sprintf("Dataset with name %s not found", body.DatasetName),
				"code":    fiber.StatusNotFound,
			})
		}
		h.logger.Error("Error fetching dataset", zap.Error(err), zap.String("dataset_id", body.DatasetName))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error validating dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}

	source, err := h.dbSourceSvc.Get(d.ID, orgID)
	if err != nil {
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			h.logger.Error("Database source not found for dataset", zap.Error(err), zap.String("dataset_id", d.ID))
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Database source not found",
				"message": fmt.Sprintf("Database source for dataset ID %s not found", d.ID),
				"code":    fiber.StatusNotFound,
			})
		}
		h.logger.Error("Error fetching database source for dataset", zap.Error(err), zap.String("dataset_id", d.ID))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error validating database source",
			"code":    fiber.StatusInternalServerError,
		})
	}

	h.logger.Info("updating database source dataset", zap.String("project_id", project.ID))

	tableName := d.Name

	var driver string

	if strings.HasPrefix(source.ConnectionString, "postgres") {
		driver = "postgres"
	} else {
		driver = "mysql"
	}

	var t time.Time
	if body.RefreshType == "incremental" && source.TimestampColumn != "" {
		t, err = time.Parse(time.RFC3339Nano, source.LastUpdatedAt)
		if err != nil {
			h.logger.Error("Error parsing last updated at timestamp", zap.Error(err), zap.String("timestamp", source.LastUpdatedAt))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error parsing last updated at timestamp",
				"code":    fiber.StatusInternalServerError,
			})
		}
	}

	if body.RefreshType == "incremental" && source.TimestampColumn == "" {
		h.logger.Error("Timestamp column is required for incremental refresh", zap.String("dataset_id", d.ID))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Timestamp column is required for incremental refresh",
			"message": "Cannot perform incremental refresh without a timestamp column",
			"code":    fiber.StatusBadRequest,
		})
	}

	refreshErr := func() error {
		if driver == "postgres" {
			if body.RefreshType == "incremental" && source.TimestampColumn != "" {
				return h.olapSvc.IncrementalRefreshPostgres(source.ConnectionString, source.SQLQuery, tableName, source.TimestampColumn, &t)
			}
			return h.olapSvc.FullTableRefreshPostgres(source.ConnectionString, source.SQLQuery, tableName)
		}
		if body.RefreshType == "incremental" && source.TimestampColumn != "" {
			return h.olapSvc.IncrementalRefreshMySQL(source.ConnectionString, source.SQLQuery, tableName, source.TimestampColumn, &t)
		}
		return h.olapSvc.FullTableRefreshMySQL(source.ConnectionString, source.SQLQuery, tableName)
	}()

	if refreshErr != nil {
		var msg string
		if body.RefreshType == "incremental" && source.TimestampColumn != "" {
			if driver == "postgres" {
				msg = "Error performing incremental refresh from postgres"
			} else {
				msg = "Error performing incremental refresh from mysql"
			}
		} else {
			if driver == "postgres" {
				msg = "Error creating table from postgres"
			} else {
				msg = "Error creating table from mysql"
			}
		}
		h.logger.Error(msg, zap.Error(refreshErr))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   refreshErr.Error(),
			"message": msg,
			"code":    fiber.StatusInternalServerError,
		})
	}

	if body.RefreshType == "incremental" && source.TimestampColumn != "" {
		lastUpdatedAt, err := h.olapSvc.GetLatestTimestamp(tableName, source.TimestampColumn)
		if err != nil {
			h.logger.Error("Error fetching latest timestamp from OLAP", zap.Error(err), zap.String("table_name", tableName), zap.String("timestamp_column", source.TimestampColumn))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error fetching latest timestamp from OLAP",
				"code":    fiber.StatusInternalServerError,
			})
		}
		if lastUpdatedAt != nil {
			err = h.dbSourceSvc.Update(ctx.Context(), models.UpdateDatabaseSourceLastUpdatedAtParams{
				ID:            source.ID,
				LastUpdatedAt: *lastUpdatedAt,
			})
		}
	}

	time.Sleep(2 * time.Second) // Wait for the table to be created in OLAP

	count, columns, err := h.getMetrics(tableName)
	if err != nil {
		h.logger.Error("Error fetching dataset metrics", zap.Error(err), zap.String("table_name", tableName))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset metrics",
			"code":    fiber.StatusInternalServerError,
		})
	}

	dataset, err := h.datasetSvc.Update(d.ID, &models.UpdateDatasetParams{
		RowCount:  count,
		Columns:   columns,
		UpdatedBy: userID,
		OrgID:     orgID,
	})
	if err != nil {
		h.logger.Error("Error creating dataset record", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset record",
			"code":    fiber.StatusInternalServerError,
		})
	}

	datasetSummary, err := h.olapSvc.GetDatasetSummary(tableName)
	if err != nil {
		h.logger.Error("Error fetching dataset summary", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	summary, err := h.datasetSvc.CreateDatasetSummary(tableName, datasetSummary)
	if err != nil {
		h.logger.Error("Error creating dataset summary", zap.Error(err))

		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	err = h.aiAgentSvc.UploadSchema(&models.SchemaParams{
		DatasetID: dataset.ID,
		ProjectID: project.ID,
	})
	if err != nil {
		h.logger.Error("Error uploading schema to AI agent", zap.Error(err))

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

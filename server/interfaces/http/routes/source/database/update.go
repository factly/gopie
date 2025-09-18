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

type updateRequestBody struct {
	ProjectID   string `json:"project_id" validate:"required,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	DatasetName string `json:"dataset_name" validate:"required,min=3" example:"gp_asdfghjklqwerty"`
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
// @Router /source/database/update [put]
func (h *httpHandler) update(ctx *fiber.Ctx) error {
	orgID := ctx.Locals(middleware.OrganizationIDHeader).(string)
	userID := ctx.Locals(middleware.UserCtxKey).(string)
	if orgID == "" {
		h.logger.Error("Organization ID header is missing")
		return ctx.Status(fiber.StatusForbidden).JSON(fiber.Map{
			"error":   "Organization ID header is required",
			"message": "Please provide the organization ID in the request header",
			"code":    fiber.StatusForbidden,
		})
	}

	// Get request body from context
	var body updateRequestBody
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

	err = h.olapSvc.DropTable(body.DatasetName)
	if err != nil {
		h.logger.Error("Error droping existing OLAP table", zap.Error(err), zap.String("table_name", body.DatasetName))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error droping existing OLAP table",
			"code":    fiber.StatusInternalServerError,
		})
	}

	tableName := d.Name

	var driver string

	if strings.HasPrefix(driver, "postgres") {
		driver = "postgres"
	} else {
		driver = "mysql"
	}

	if driver == "postgres" {
		err := h.olapSvc.CreateTableFromPostgres(source.ConnectionString, source.SQLQuery, tableName)
		if err != nil {
			h.logger.Error("Error creating table from postgres", zap.Error(err))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error creating table from postgres",
				"code":    fiber.StatusInternalServerError,
			})
		}
	} else {
		err := h.olapSvc.CreateTableFromMySql(source.ConnectionString, source.SQLQuery, tableName)
		if err != nil {
			h.logger.Error("Error creating table from mysql", zap.Error(err))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error creating table from mysql",
				"code":    fiber.StatusInternalServerError,
			})
		}
	}

	time.Sleep(2 * time.Second) // Wait for the table to be created in OLAP

	count, columns, err := h.getMetrics(tableName)
	if err != nil {
		h.logger.Error("Error fetching dataset metrics", zap.Error(err), zap.String("table_name", tableName))

		// Clean up the created OLAP table since metrics fetch failed
		dropErr := h.olapSvc.DropTable(tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", tableName))
		}

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
	})
	if err != nil {
		h.logger.Error("Error creating dataset record", zap.Error(err))

		// Clean up the created OLAP table since dataset record creation failed
		dropErr := h.olapSvc.DropTable(tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", tableName))
		}

		deleteErr := h.dbSourceSvc.Delete(source.ID)
		if deleteErr != nil {
			h.logger.Error("Failed to delete database source during cleanup", zap.Error(deleteErr), zap.String("source_id", source.ID))
		}

		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset record",
			"code":    fiber.StatusInternalServerError,
		})
	}

	datasetSummary, err := h.olapSvc.GetDatasetSummary(tableName)
	if err != nil {
		h.logger.Error("Error fetching dataset summary", zap.Error(err))

		// Clean up the dataset record and OLAP table since dataset summary fetch failed
		deleteErr := h.datasetSvc.Delete(dataset.ID, dataset.OrgID)
		if deleteErr != nil {
			h.logger.Error("Failed to delete dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", dataset.ID))
		}

		deleteSErr := h.dbSourceSvc.Delete(source.ID)
		if deleteSErr != nil {
			h.logger.Error("Failed to delete database source during cleanup", zap.Error(deleteSErr), zap.String("source_id", source.ID))
		}

		dropErr := h.olapSvc.DropTable(tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", tableName))
		}

		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	summary, err := h.datasetSvc.CreateDatasetSummary(tableName, datasetSummary)
	if err != nil {
		h.logger.Error("Error creating dataset summary", zap.Error(err))

		// Clean up the dataset record and OLAP table since dataset summary creation failed
		deleteErr := h.datasetSvc.Delete(dataset.ID, dataset.OrgID)
		if deleteErr != nil {
			h.logger.Error("Failed to delete dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", dataset.ID))
		}

		dropErr := h.olapSvc.DropTable(tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", tableName))
		}

		deleteSErr := h.dbSourceSvc.Delete(source.ID)
		if deleteSErr != nil {
			h.logger.Error("Failed to delete database source during cleanup", zap.Error(deleteSErr), zap.String("source_id", source.ID))
		}

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

		// Clean up all created resources since schema upload failed
		summaryErr := h.datasetSvc.DeleteDatasetSummary(tableName)
		if summaryErr != nil {
			h.logger.Error("Failed to delete dataset summary during cleanup", zap.Error(summaryErr), zap.String("dataset_name", tableName))
		}

		deleteSErr := h.dbSourceSvc.Delete(source.ID)
		if deleteSErr != nil {
			h.logger.Error("Failed to delete database source during cleanup", zap.Error(deleteSErr), zap.String("source_id", source.ID))
		}

		deleteErr := h.datasetSvc.Delete(dataset.ID, dataset.OrgID)
		if deleteErr != nil {
			h.logger.Error("Failed to delete dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", dataset.ID))
		}

		dropErr := h.olapSvc.DropTable(tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", tableName))
		}

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

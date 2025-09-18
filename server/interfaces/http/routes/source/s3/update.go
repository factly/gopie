package s3

import (
	"fmt"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// updateRequestBody represents the request body for updating a dataset from S3
// @Description Request body for updating a dataset from S3
type updateRequestBody struct {
	// Name of the dataset to update
	Dataset string `json:"dataset" validate:"required" example:"sales_data_table"`
	// Column names to be altered (optional)
	AlterColumnNames map[string]string `json:"alter_column_names,omitempty" validate:"omitempty,dive,required"`
	// Column descriptions
	ColumnDescriptions map[string]string `json:"column_descriptions,omitempty" validate:"omitempty,dive,required"`
	// Project ID of the dataset
	ProjectID    string `json:"project_id" validate:"required,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	IgnoreErrors bool   `json:"ignore_errors"`
	CustomPrompt string `json:"custom_prompt"`
}

// @Summary Update dataset from S3
// @Description Update an existing dataset with a new file from S3
// @Tags s3
// @Accept json
// @Produce json
// @Param body body updateRequestBody true "Update request parameters"
// @Success 200 {object} responses.SuccessResponse{data=models.Dataset}
// @Failure 400 {object} responses.ErrorResponse "Invalid request body or S3 file access error"
// @Failure 404 {object} responses.ErrorResponse "Dataset not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /source/s3/update [post]
func (h *httpHandler) update(ctx *fiber.Ctx) error {
	// Get request body from context
	body := updateRequestBody{
		IgnoreErrors: true,
	}
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
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)
	userID := ctx.Locals(middleware.UserCtxKey).(string)

	// Check if dataset exists
	d, err := h.datasetSvc.GetByTableName(body.Dataset, orgID)
	if err != nil {
		if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
			h.logger.Error("Dataset not found", zap.Error(err), zap.String("dataset_id", body.Dataset))
			return ctx.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error":   "Dataset not found",
				"message": fmt.Sprintf("Dataset with name %s not found", body.Dataset),
				"code":    fiber.StatusNotFound,
			})
		}
		h.logger.Error("Error fetching dataset", zap.Error(err), zap.String("dataset_id", body.Dataset))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error validating dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// We perform updates by droping the existing OLAP table and re-ingesting the new file

	err = h.olapSvc.DropTable(d.Name)
	if err != nil {
		h.logger.Error("Error droping existing OLAP table", zap.Error(err), zap.String("table_name", d.Name))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error droping existing OLAP table",
			"code":    fiber.StatusInternalServerError,
		})
	}

	h.logger.Info("Starting file update", zap.String("file_path", d.FilePath), zap.String("dataset_id", d.ID))

	originalDataset := d
	originalFilePath := d.FilePath
	originalColumns := d.Columns
	originalRowCount := d.RowCount
	originalSize := d.Size

	// Upload file to OLAP service
	res, err := h.olapSvc.IngestS3File(ctx.Context(), d.FilePath, d.Name, body.AlterColumnNames, body.IgnoreErrors)
	if err != nil {
		h.logger.Error("Error uploading file to OLAP service", zap.Error(err), zap.String("file_path", d.FilePath))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Failed to upload file from S3. Please check if the file exists and you have proper access.",
			"code":    fiber.StatusBadRequest,
		})
	}

	count, columns, err := h.getMetrics(res.TableName)
	if err != nil {
		h.logger.Error("Error fetching dataset metrics", zap.Error(err), zap.String("table_name", res.TableName))
		// Clean up the updated OLAP table since metrics fetch failed
		dropErr := h.olapSvc.DropTable(res.TableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", res.TableName))
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset metrics",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// update dataset entry for successful upload
	dataset, err := h.datasetSvc.Update(d.ID, &models.UpdateDatasetParams{
		RowCount:  int(count),
		Size:      res.Size,
		Columns:   columns,
		UpdatedBy: userID,
	})
	if err != nil {
		h.logger.Error("Error updating dataset record", zap.Error(err))
		// Clean up the updated OLAP table since dataset update failed
		dropErr := h.olapSvc.DropTable(res.TableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", res.TableName))
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error updating dataset record",
			"code":    fiber.StatusInternalServerError,
		})
	}

	err = h.datasetSvc.DeleteDatasetSummary(res.TableName)
	if err != nil {
		h.logger.Error("Error deleting existing dataset summary", zap.Error(err))
		// Clean up the dataset record and OLAP table since dataset summary deletion failed
		_, deleteErr := h.datasetSvc.Update(d.ID, &models.UpdateDatasetParams{
			Description:  originalDataset.Description,
			FilePath:     originalFilePath,
			RowCount:     originalRowCount,
			Size:         originalSize,
			Columns:      originalColumns,
			UpdatedBy:    userID,
			CustomPrompt: body.CustomPrompt,
		})
		if deleteErr != nil {
			h.logger.Error("Failed to revert dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", d.ID))
		}
		dropErr := h.olapSvc.DropTable(res.TableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr),
				zap.String("table_name", res.TableName))
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error deleting existing dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	datasetSummary, err := h.olapSvc.GetDatasetSummary(res.TableName)
	if err != nil {
		h.logger.Error("Error fetching dataset summary", zap.Error(err))
		// Clean up the dataset record and OLAP table since dataset summary fetch failed
		deleteErr := h.datasetSvc.Delete(dataset.ID, dataset.OrgID)
		if deleteErr != nil {
			h.logger.Error("Failed to delete dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", dataset.ID))
		}
		dropErr := h.olapSvc.DropTable(res.TableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", res.TableName))
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	summary, err := h.datasetSvc.CreateDatasetSummary(res.TableName, datasetSummary)
	if err != nil {
		h.logger.Error("Error creating dataset summary", zap.Error(err))
		// Clean up the dataset record and OLAP table since dataset summary creation failed
		_, deleteErr := h.datasetSvc.Update(d.ID, &models.UpdateDatasetParams{
			Description:  originalDataset.Description,
			FilePath:     originalFilePath,
			RowCount:     originalRowCount,
			Size:         originalSize,
			Columns:      originalColumns,
			UpdatedBy:    userID,
			CustomPrompt: body.CustomPrompt,
		})
		if deleteErr != nil {
			h.logger.Error("Failed to revert dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", d.ID))
		}
		dropErr := h.olapSvc.DropTable(res.TableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", res.TableName))
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	err = h.aiAgentSvc.UploadSchema(&models.SchemaParams{
		DatasetID: dataset.ID,
		ProjectID: body.ProjectID,
	})
	if err != nil {
		h.logger.Error("Error uploading schema to AI agent", zap.Error(err))
		// Clean up all created resources since schema upload failed
		if summary != nil {
			summaryErr := h.datasetSvc.DeleteDatasetSummary(res.TableName)
			if summaryErr != nil {
				h.logger.Error("Failed to delete dataset summary during cleanup", zap.Error(summaryErr), zap.String("dataset_name", res.TableName))
			}
		}
		_, deleteErr := h.datasetSvc.Update(d.ID, &models.UpdateDatasetParams{
			Description:  originalDataset.Description,
			FilePath:     originalFilePath,
			RowCount:     originalRowCount,
			Size:         originalSize,
			Columns:      originalColumns,
			UpdatedBy:    userID,
			CustomPrompt: body.CustomPrompt,
		})
		if deleteErr != nil {
			h.logger.Error("Failed to revert dataset during cleanup", zap.Error(deleteErr), zap.String("dataset_id", d.ID))
		}
		dropErr := h.olapSvc.DropTable(res.TableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup", zap.Error(dropErr), zap.String("table_name", res.TableName))
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error uploading schema to AI agent",
			"code":    fiber.StatusInternalServerError,
		})
	}

	h.logger.Info("File update completed successfully",
		zap.String("dataset_id", dataset.ID))

	return ctx.Status(fiber.StatusOK).JSON(map[string]any{
		"data": map[string]any{
			"dataset": dataset,
			"summary": summary,
		},
	})
}

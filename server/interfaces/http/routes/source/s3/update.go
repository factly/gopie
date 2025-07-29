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
	// S3 path of the new file (optional)
	FilePath string `json:"file_path,omitempty" validate:"omitempty,min=1" example:"my-bucket/data/updated_sales.csv"`
	// Updated description of the dataset (optional)
	Description string `json:"description,omitempty" validate:"omitempty,min=10,max=500" example:"Updated sales data for Q1 2024"`
	// Name of the dataset to update
	Dataset string `json:"dataset" validate:"required" example:"sales_data_table"`
	// User ID of the updater
	UpdatedBy string `json:"updated_by" validate:"required" example:"550e8400-e29b-41d4-a716-446655440000"`
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

	h.logger.Info("Starting file update", zap.String("file_path", body.FilePath), zap.String("dataset_id", d.ID))

	// if filepath is not provided, use the existing filepath
	filePath := body.FilePath
	if filePath == "" {
		filePath = d.FilePath
	}

	// Store original state in case we need to rollback
	originalDataset := d

	// Upload file to OLAP service
	res, err := h.olapSvc.IngestS3File(ctx.Context(), filePath, d.Name, body.AlterColumnNames, body.IgnoreErrors)
	if err != nil {
		h.logger.Error("Error uploading file to OLAP service", zap.Error(err), zap.String("file_path", filePath))

		// Create failed upload record
		f, e := h.datasetSvc.CreateFailedUpload(d.ID, err.Error())
		if e != nil {
			h.logger.Error("Error creating failed upload record", zap.Error(e))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   e.Error(),
				"message": "Error creating failed upload record",
				"code":    fiber.StatusInternalServerError,
			})
		}

		// For S3 upload failures, return a more specific error
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Failed to upload file from S3. Please check if the file exists and you have proper access.",
			"code":    fiber.StatusBadRequest,
			"data":    f,
		})
	}

	count, columns, err := h.getMetrics(res.TableName)
	if err != nil {
		h.logger.Error("Error fetching dataset metrics", zap.Error(err), zap.String("table_name", res.TableName))

		// Try to revert back to original data if possible
		_, revertErr := h.olapSvc.IngestS3File(ctx.Context(), originalDataset.FilePath, originalDataset.Name, nil, body.IgnoreErrors)
		if revertErr != nil {
			h.logger.Error("Failed to revert table to original state", zap.Error(revertErr))
		}

		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching metrics",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// update dataset entry for successful upload
	dataset, err := h.datasetSvc.Update(d.ID, &models.UpdateDatasetParams{
		Description:  body.Description,
		FilePath:     filePath,
		RowCount:     int(count),
		Size:         res.Size,
		Columns:      columns,
		UpdatedBy:    body.UpdatedBy,
		CustomPrompt: body.CustomPrompt,
	})
	if err != nil {
		h.logger.Error("Error updating dataset record", zap.Error(err))

		// Try to revert back to original data
		_, revertErr := h.olapSvc.IngestS3File(ctx.Context(), originalDataset.FilePath, originalDataset.Name, nil, body.IgnoreErrors)
		if revertErr != nil {
			h.logger.Error("Failed to revert table to original state", zap.Error(revertErr))
		}

		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error updating dataset record",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// Get dataset summary if column descriptions were provided
	var summary *models.DatasetSummaryWithName
	if len(body.ColumnDescriptions) > 0 {
		datasetSummary, err := h.olapSvc.GetDatasetSummary(res.TableName)
		if err != nil {
			h.logger.Error("Error fetching dataset summary", zap.Error(err))

			// Don't roll back at this point since the data update was successful
			// Just continue without summary update

			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   err.Error(),
				"message": "Error fetching dataset summary",
				"code":    fiber.StatusInternalServerError,
			})
		}

		if datasetSummary != nil {
			summaryMap := make(map[string]int)
			for i := range *datasetSummary {
				summaryMap[(*datasetSummary)[i].ColumnName] = i
			}

			for colName, desc := range body.ColumnDescriptions {
				if desc != "" {
					if idx, exists := summaryMap[colName]; exists {
						(*datasetSummary)[idx].Description = desc
					}
				}
			}

			// Update dataset summary
			summary, err = h.datasetSvc.CreateDatasetSummary(res.TableName, datasetSummary)
			if err != nil {
				h.logger.Error("Error creating dataset summary", zap.Error(err))

				// Continue without summary since data update was successful

				return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
					"error":   err.Error(),
					"message": "Error creating dataset summary",
					"code":    fiber.StatusInternalServerError,
				})
			}
		}
	}

	// Update schema in AI agent if needed
	err = h.aiAgentSvc.UploadSchema(&models.UploadSchemaParams{
		DatasetID: dataset.ID,
		ProjectID: body.ProjectID,
	})
	if err != nil {
		h.logger.Error("Error uploading schema to AI agent", zap.Error(err))
		// We don't fail the entire update if schema upload fails
		// Just log the error and continue
	}

	h.logger.Info("File update completed successfully",
		zap.String("dataset_id", dataset.ID))

	// Return success response
	return ctx.Status(fiber.StatusOK).JSON(map[string]any{
		"data": map[string]any{
			"dataset": dataset,
			"summary": summary,
		},
	})
}

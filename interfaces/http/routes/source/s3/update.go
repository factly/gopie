package s3

import (
	"fmt"
	"os"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type updateRequestBody struct {
	FilePath    string `json:"file_path,omitempty" validate:"omitempty,min=1"`
	Description string `json:"description,omitempty" validate:"omitempty,min=10,max=500"`
	Dataset     string `json:"dataset" validate:"required"`
}

// upload files to gopie from s3
func (h *httpHandler) update(ctx *fiber.Ctx) error {
	// Get request body from context
	body := ctx.Locals("body").(*updateRequestBody)

	// Check if d exists
	d, err := h.datasetSvc.GetByTableName(body.Dataset)
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

	h.logger.Info("Starting file upload", zap.String("file_path", body.FilePath), zap.String("dataset_id", d.ID))

	// if filepath is not provided, use the existing filepath
	filePath := body.FilePath
	if filePath == "" {
		filePath = d.FilePath
	}

	// Upload file to OLAP service
	res, err := h.olapSvc.UploadFile(ctx.Context(), filePath, d.Name)
	if err != nil {
		h.logger.Error("Error uploading file to OLAP service", zap.Error(err), zap.String("file_path", body.FilePath))

		// For S3 upload failures, return a more specific error
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Failed to upload file from S3. Please check if the file exists and you have proper access.",
			"code":    fiber.StatusBadRequest,
		})
	}

	// Get row count of uploaded table
	countSql := "select count(*) from " + res.TableName
	countResult, err := h.olapSvc.ExecuteQuery(countSql)
	if err != nil {
		h.logger.Error("Error fetching row count", zap.Error(err), zap.String("table", res.TableName))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": fmt.Sprintf("Error fetching row count for table %s", res.TableName),
			"code":    fiber.StatusInternalServerError,
		})
	}

	// Extract count value from result with improved type checking
	count, ok := countResult[0]["count_star()"].(int64)
	if !ok {
		h.logger.Error("Invalid count result type", zap.Any("count_result", countResult[0]["count_star()"]))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "Invalid count result type",
			"message": "Error processing row count",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// Get column descriptions
	columns, err := h.olapSvc.ExecuteQuery("desc " + res.TableName)
	if err != nil {
		h.logger.Error("Error fetching column descriptions", zap.Error(err), zap.String("table", res.TableName))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": fmt.Sprintf("Error fetching column descriptions for table %s", res.TableName),
			"code":    fiber.StatusInternalServerError,
		})
	}

	// update dataset entry for successful upload
	dataset, err := h.datasetSvc.Update(d.ID, &models.UpdateDatasetParams{
		Description: body.Description,
		Format:      res.Format,
		FilePath:    filePath,
		RowCount:    int(count),
		Size:        res.Size,
		Columns:     columns,
	})
	if err != nil {
		h.logger.Error("Error updating dataset record", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error updating dataset record",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// Cleanup temporary file
	if err = os.Remove(res.FilePath); err != nil {
		h.logger.Error("Error deleting temporary file",
			zap.Error(err),
			zap.String("file_path", res.FilePath),
			zap.String("dataset_id", dataset.ID))
	}

	h.logger.Info("File upload completed successfully",
		zap.String("dataset_id", dataset.ID))

	// Return success response
	return ctx.Status(fiber.StatusCreated).JSON(map[string]interface{}{
		"data": dataset,
	})
}

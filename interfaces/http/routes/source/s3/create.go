package s3

import (
	"fmt"
	"os"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type uploadRequestBody struct {
	FilePath    string `json:"file_path" validate:"required,min=1"`
	Description string `json:"description,omitempty" validate:"omitempty,min=10,max=500"`
	ProjectID   string `json:"project_id" validate:"required,uuid"`
}

// upload files to gopie from s3
func (h *httpHandler) upload(ctx *fiber.Ctx) error {
	// Get request body from context
	body := ctx.Locals("body").(*uploadRequestBody)

	// Check if project exists
	project, err := h.projectSvc.Details(body.ProjectID)
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

	h.logger.Info("Starting file upload", zap.String("file_path", body.FilePath), zap.String("project_id", project.ID))

	// Upload file to OLAP service
	res, err := h.olapSvc.UploadFile(ctx.Context(), body.FilePath)
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

	// Create dataset entry for successful upload
	dataset, err := h.datasetSvc.Create(&models.CreateDatasetParams{
		Name:        res.TableName,
		Description: body.Description,
		ProjectID:   body.ProjectID,
		Columns:     columns,
		Format:      res.Format,
		FilePath:    body.FilePath,
		RowCount:    int(count),
		Size:        res.Size,
	})
	if err != nil {
		h.logger.Error("Error creating dataset record", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset record",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// Cleanup temporary file
	if err = os.Remove(res.FilePath); err != nil {
		h.logger.Error("Error deleting temporary file",
			zap.Error(err),
			zap.String("file_path", res.FilePath),
			zap.String("dataset_id", dataset.ID))
		// Continue execution as this is not a critical error
	}

	h.logger.Info("File upload completed successfully",
		zap.String("dataset_id", dataset.ID),
		zap.String("project_id", project.ID))

	// Return success response
	return ctx.Status(fiber.StatusCreated).JSON(map[string]interface{}{
		"data": dataset,
	})
}

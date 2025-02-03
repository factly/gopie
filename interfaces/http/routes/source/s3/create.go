package s3

import (
	"os"

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

	// Upload file to OLAP service
	res, err := h.olapSvc.UploadFile(ctx.Context(), body.FilePath)
	if err != nil {
		// Create dataset entry for failed upload
		dataset, e := h.datasetSvc.Create(&models.CreateDatasetParams{
			Name:        res.TableName,
			Description: body.Description,
			ProjectID:   body.ProjectID,
			FilePath:    body.FilePath,
		})
		if e != nil {
			h.logger.Error("Error creating failed dataset upload", zap.Error(e))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   e.Error(),
				"message": "error uploading data | error creating failed dataset upload",
				"code":    fiber.StatusInternalServerError,
			})
		}

		// Record failed upload details
		failed, e := h.datasetSvc.CreateFailedUpload(dataset.ID, err.Error())
		if e != nil {
			h.logger.Error("Error creating failed dataset upload", zap.Error(e))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   e.Error(),
				"message": "error uploading data | error creating failed dataset upload",
				"code":    fiber.StatusInternalServerError,
			})
		}
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "error uploading file",
			"code":    fiber.StatusInternalServerError,
			"data":    failed,
		})
	}

	// Get row count of uploaded table
	countSql := "select count(*) from " + res.TableName
	countResult, err := h.olapSvc.ExecuteQuery(countSql)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "error fetching count",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// Extract count value from result
	count, ok := countResult[0]["count_star()"].(int64)
	if !ok {
		return fiber.NewError(fiber.StatusInternalServerError, "error fetching count")
	}

	// Get column descriptions
	columns, err := h.olapSvc.ExecuteQuery("desc " + res.TableName)
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "error fetching columns",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// Create dataset entry for successful upload
	dataset, err := h.datasetSvc.Create(&models.CreateDatasetParams{
		Name:        res.TableName,
		Description: "Dataset created from S3",
		ProjectID:   body.ProjectID,
		Columns:     columns,
		Format:      res.Format,
		FilePath:    body.FilePath,
		RowCount:    int(count),
		Size:        res.Size,
	})
	if err != nil {
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "error creating dataset",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// Cleanup temporary file
	err = os.Remove(res.FilePath)
	if err != nil {
		h.logger.Error("Error deleting file from tmp dir you might to delete it manually", zap.Error(err))
	}

	// Return success response
	return ctx.Status(fiber.StatusCreated).JSON(map[string]interface{}{
		"data": dataset,
	})
}

package s3

import (
	"fmt"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/go-playground/validator/v10"
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
	var body updateRequestBody
	if err := ctx.BodyParser(&body); err != nil {
		h.logger.Info("Error parsing request body", zap.Error(err))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Invalid request body format",
			"code":    fiber.StatusBadRequest,
		})
	}
	validate := validator.New()

	if err := validate.Struct(body); err != nil {
		var errors []models.ValidationError
		for _, err := range err.(validator.ValidationErrors) {
			errors = append(errors, models.ValidationError{
				Field: err.Field(),
				Tag:   err.Tag(),
				Value: err.Param(),
			})
		}
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   errors,
			"message": "Invalid request body",
			"code":    fiber.StatusBadRequest,
		})
	}

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
	res, err := h.olapSvc.IngestS3File(ctx.Context(), filePath, d.Name)
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

	h.logger.Info("File upload completed successfully",
		zap.String("dataset_id", dataset.ID))

	// Return success response
	return ctx.Status(fiber.StatusCreated).JSON(map[string]interface{}{
		"data": dataset,
	})
}

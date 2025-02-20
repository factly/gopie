package s3

import (
	"fmt"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/go-playground/validator/v10"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// uploadRequestBody represents the request body for uploading a file from S3
// @Description Request body for uploading a file from S3
type uploadRequestBody struct {
	// S3 path of the file to upload
	FilePath string `json:"file_path" validate:"required,min=1" example:"my-bucket/data/sales.csv"`
	// Description of the dataset
	Description string `json:"description,omitempty" validate:"omitempty,min=10,max=500" example:"Sales data for Q1 2024"`
	// ID of the project to add the dataset to
	ProjectID string `json:"project_id" validate:"required,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	// User ID of the creator
	CreatedBy string `json:"created_by" validate:"required" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Alias of the dataset
	Alias string `json:"alias" validate:"omitempty,min=3" example:"sales_data"`
}

// @Summary Upload file from S3
// @Description Upload a file from S3 and create a new dataset
// @Tags s3
// @Accept json
// @Produce json
// @Param body body uploadRequestBody true "Upload request parameters"
// @Success 201 {object} responses.SuccessResponse{data=models.Dataset}
// @Failure 400 {object} responses.ErrorResponse "Invalid request body or S3 file access error"
// @Failure 404 {object} responses.ErrorResponse "Project not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /source/s3/upload [post]
func (h *httpHandler) upload(ctx *fiber.Ctx) error {
	// Get request body from context
	var body uploadRequestBody
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
	res, err := h.olapSvc.IngestS3File(ctx.Context(), body.FilePath, "")
	if err != nil {
		h.logger.Error("Error uploading file to OLAP service", zap.Error(err), zap.String("file_path", body.FilePath))

		dataset, e := h.datasetSvc.Create(&models.CreateDatasetParams{
			Name:        res.TableName,
			Description: body.Description,
			ProjectID:   project.ID,
			Format:      res.Format,
			FilePath:    res.FilePath,
			Size:        res.Size,
			UpdatedBy:   body.CreatedBy,
			CreatedBy:   body.CreatedBy,
			Alias:       body.Alias,
		})
		if e != nil {
			h.logger.Error("Error creating dataset record", zap.Error(e))
			return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   e.Error(),
				"message": "Error creating failed dataset record",
				"code":    fiber.StatusInternalServerError,
			})
		}

		f, e := h.datasetSvc.CreateFailedUpload(dataset.ID, err.Error())
		if e != nil {
			h.logger.Error("Error creating failed upload record", zap.Error(err))
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
		ProjectID:   project.ID,
		Columns:     columns,
		Format:      res.Format,
		FilePath:    res.FilePath,
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

	h.logger.Info("File upload completed successfully",
		zap.String("dataset_id", dataset.ID),
		zap.String("project_id", project.ID))

	// Return success response
	return ctx.Status(fiber.StatusCreated).JSON(map[string]interface{}{
		"data": dataset,
	})
}

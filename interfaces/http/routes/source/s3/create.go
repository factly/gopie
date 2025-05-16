package s3

import (
	"fmt"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
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
	Alias string `json:"alias" validate:"required,min=3" example:"sales_data"`
	// Column names to be altered
	AlterColumnNames map[string]string `json:"alter_column_names,omitempty" validate:"omitempty,dive,required"`
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

	err := pkg.ValidateRequest(h.logger, &body)
	if err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
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
	res, err := h.olapSvc.IngestS3File(ctx.Context(), body.FilePath, "", body.AlterColumnNames)
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

	count, columns, err := h.getMetrics(res.TableName)
	if err != nil {
		h.logger.Error("Error fetching dataset metrics", zap.Error(err), zap.String("table_name", res.TableName))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset metrics",
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
		RowCount:    count,
		Size:        res.Size,
		Alias:       body.Alias,
		CreatedBy:   body.CreatedBy,
		UpdatedBy:   body.CreatedBy,
	})
	if err != nil {
		h.logger.Error("Error creating dataset record", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset record",
			"code":    fiber.StatusInternalServerError,
		})
	}

	datasetSummary, err := h.olapSvc.GetDatasetSummary(res.TableName)
	if err != nil {
		h.logger.Error("Error fetching dataset summary", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	summary, err := h.datasetSvc.CreateDatasetSummary(res.TableName, datasetSummary)
	if err != nil {
		h.logger.Error("Error creating dataset summary", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	err = h.aiAgentSvc.UploadSchema(&models.UploadSchemaParams{
		DatasetID: dataset.ID,
		ProjectID: project.ID,
		FilePath:  res.FilePath,
	})
	if err != nil {
		h.logger.Error("Error uploading schema to AI agent", zap.Error(err)) // No need to return error
	}

	h.logger.Info("File upload completed successfully",
		zap.String("dataset_id", dataset.ID),
		zap.String("project_id", project.ID))

	// Return success response
	return ctx.Status(fiber.StatusCreated).JSON(map[string]any{
		"data": map[string]any{
			"dataset": dataset,
			"summary": summary,
		},
	})
}

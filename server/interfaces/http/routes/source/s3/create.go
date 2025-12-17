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

// uploadRequestBody represents the request body for uploading a file from S3
// @Description Request body for uploading a file from S3
type uploadRequestBody struct {
	// S3 path of the file to upload
	FilePath string `json:"file_path" validate:"required,min=1" example:"my-bucket/data/sales.csv"`
	// Description of the dataset
	Description string `json:"description,omitempty" validate:"omitempty,min=10,max=1000" example:"Sales data for Q1 2024"`
	// ID of the project to add the dataset to
	ProjectID string `json:"project_id" validate:"required,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	// Alias of the dataset
	Alias              string            `json:"alias" validate:"required,min=3" example:"sales_data"`
	AlterColumnNames   map[string]string `json:"alter_column_names,omitempty" validate:"omitempty"`
	ColumnDescriptions map[string]string `json:"column_descriptions,omitempty" validate:"omitempty"`
	IgnoreErrors       bool              `json:"ignore_errors"`
	CustomPrompt       string            `json:"custom_prompt"`
}

// resourceCleanup defines what resources need to be cleaned up in case of an error
type resourceCleanup struct {
	tableName  string
	datasetID  string
	orgID      string
	userID     string
	role       models.Role
	hasDataset bool
	hasSummary bool
}

// cleanupResources handles cleanup of created resources in case of errors
func (h *httpHandler) cleanupResources(rc resourceCleanup) {
	// Delete dataset summary if it was created
	if rc.hasSummary {
		summaryErr := h.datasetSvc.DeleteDatasetSummary(rc.tableName)
		if summaryErr != nil {
			h.logger.Error("Failed to delete dataset summary during cleanup",
				zap.Error(summaryErr),
				zap.String("dataset_name", rc.tableName))
		}
	}

	// Delete dataset record if it was created
	if rc.hasDataset {
		deleteErr := h.datasetSvc.Delete(rc.datasetID, rc.orgID, rc.userID, rc.role)
		if deleteErr != nil {
			h.logger.Error("Failed to delete dataset during cleanup",
				zap.Error(deleteErr),
				zap.String("dataset_id", rc.datasetID))
		}
	}

	// Always try to drop the table if tableName is provided
	if rc.tableName != "" {
		dropErr := h.olapSvc.DropTable(rc.tableName)
		if dropErr != nil {
			h.logger.Error("Failed to drop table during cleanup",
				zap.Error(dropErr),
				zap.String("table_name", rc.tableName))
		}
	}
}

// @Summary Upload file from S3
// @Description Upload a file from S3 and create a new dataset
// @Tags s3
// @Accept json
// @Produce json
// @Param body body uploadRequestBody true "Upload request parameters"
// @Success 201 {object} responses.SuccessResponse{data=map[string]interface{}{"dataset":models.Dataset,"summary":any}}
// @Failure 400 {object} responses.ErrorResponse "Invalid request body or S3 file access error"
// @Failure 404 {object} responses.ErrorResponse "Project not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /source/s3/upload [post]
func (h *httpHandler) upload(ctx *fiber.Ctx) error {
	orgID := ctx.Get(middleware.OrganizationIDHeader)
	userID := ctx.Get(middleware.UserCtxKey)
	role := ctx.Locals(middleware.RoleCtxKey).(models.Role)
	if orgID == "" {
		h.logger.Error("Organization ID header is missing")
		return ctx.Status(fiber.StatusForbidden).JSON(fiber.Map{
			"error":   "Organization ID header is required",
			"message": "Please provide the organization ID in the request header",
			"code":    fiber.StatusForbidden,
		})
	}
	// Get request body from context
	body := uploadRequestBody{
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

	// Check if project exists
	project, err := h.projectSvc.Details(body.ProjectID, orgID, userID, role)
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
	res, err := h.olapSvc.IngestS3File(nil, ctx.Context(), body.FilePath, "", body.AlterColumnNames, body.IgnoreErrors)
	if err != nil {
		h.logger.Error("Error uploading file to OLAP service", zap.Error(err), zap.String("file_path", body.FilePath))

		// For S3 upload failures, return a more specific error
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Failed to upload file from S3. Please check if the file exists and you have proper access.",
			"code":    fiber.StatusBadRequest,
		})
	}

	// Initialize cleanup resource object
	cleanup := resourceCleanup{
		tableName: res.TableName,
	}

	count, columns, err := h.getMetrics(res.TableName)
	if err != nil {
		h.logger.Error("Error fetching dataset metrics", zap.Error(err), zap.String("table_name", res.TableName))
		h.cleanupResources(cleanup)
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error fetching dataset metrics",
			"code":    fiber.StatusInternalServerError,
		})
	}

	dataset, err := h.datasetSvc.Create(&models.CreateDatasetParams{
		Name:         res.TableName,
		Description:  body.Description,
		ProjectID:    project.ID,
		Columns:      columns,
		FilePath:     res.FilePath,
		RowCount:     count,
		Size:         res.Size,
		Alias:        body.Alias,
		CreatedBy:    userID,
		UpdatedBy:    userID,
		Source:       "file",
		OrgID:        orgID,
		CustomPrompt: body.CustomPrompt,
	})
	if err != nil {
		h.logger.Error("Error creating dataset record", zap.Error(err))
		h.cleanupResources(cleanup)
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset record",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// Update cleanup object to include dataset info
	cleanup.hasDataset = true
	cleanup.datasetID = dataset.ID
	cleanup.orgID = dataset.OrgID

	datasetSummary, err := h.olapSvc.GetDatasetSummary(res.TableName)
	if err != nil {
		h.logger.Error("Error fetching dataset summary", zap.Error(err))
		h.cleanupResources(cleanup)
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
	}

	summary, err := h.datasetSvc.CreateDatasetSummary(res.TableName, datasetSummary)
	if err != nil {
		h.logger.Error("Error creating dataset summary", zap.Error(err))
		h.cleanupResources(cleanup)
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// Update cleanup object to include summary info
	cleanup.hasSummary = true

	err = h.aiAgentSvc.UploadSchema(&models.SchemaParams{
		DatasetID: dataset.ID,
		ProjectID: project.ID,
	})
	if err != nil {
		h.logger.Error("Error uploading schema to AI agent", zap.Error(err))
		h.cleanupResources(cleanup)
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error uploading schema to AI agent",
			"code":    fiber.StatusInternalServerError,
		})
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

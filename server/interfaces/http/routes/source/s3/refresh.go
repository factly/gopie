package s3

import (
	"context"
	"fmt"
	"time"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// refreshRequestBody represents the request body for updating a dataset from S3
// @Description Request body for updating a dataset from S3
type refreshRequestBody struct {
	// Name of the dataset to update
	DatasetName  string `json:"dataset_name" validate:"required" example:"sales_data_table"`
	FilePath     string `json:"file_path" validate:"required,min=1" example:"my-bucket/data/sales.csv"`
	ProjectID    string `json:"project_id" validate:"required,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	IgnoreErrors bool   `json:"ignore_errors"`
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
// @Router /source/s3/refresh [post]
func (h *httpHandler) refresh(ctx *fiber.Ctx) error {
	// Get request body from context
	body := refreshRequestBody{
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

	h.logger.Info("Dataset found, proceeding with update", zap.String("dataset_id", d.ID), zap.String("table_name", d.Name))

	olapDB := h.olapSvc.GetDB()
	storeDB := h.datasetSvc.GetDB()
	txCtx := context.Background()

	olapTx, err := olapDB.Begin()
	if err != nil {
		h.logger.Error("Error starting OLAP transaction", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error starting OLAP transaction",
			"code":    fiber.StatusInternalServerError,
		})
	}

	storeTx, err := storeDB.Begin(txCtx)
	if err != nil {
		h.logger.Error("Error starting Store transaction", zap.Error(err))
		olapTx.Rollback()
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error starting Store transaction",
			"code":    fiber.StatusInternalServerError,
		})
	}

	// Ensure transactions are committed or rolled back
	defer func() {
		if err != nil {
			h.logger.Error("Rolling back transactions due to error", zap.Error(err))
			olapTx.Rollback()
			storeTx.Rollback(txCtx)
		} else {
			h.logger.Info("Committing transactions")
			olapTx.Commit()
			storeTx.Commit(txCtx)
		}
	}()

	err = h.olapSvc.DropTableWithTx(olapTx, d.Name)
	if err != nil {
		// will not rollback here as there are no changes yet
		h.logger.Error("Error droping existing OLAP table", zap.Error(err), zap.String("table_name", d.Name))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error droping existing OLAP table",
			"code":    fiber.StatusInternalServerError,
		})
	}

	h.logger.Info("Starting file update", zap.String("file_path", d.FilePath), zap.String("dataset_id", d.ID))

	// override file path if provided
	if body.FilePath != "" {
		d.FilePath = body.FilePath
	}

	// Upload file to OLAP service
	res, err := h.olapSvc.IngestS3File(olapTx, ctx.Context(), d.FilePath, d.Name, nil, body.IgnoreErrors)
	if err != nil {
		h.logger.Error("Error uploading file to OLAP service", zap.Error(err), zap.String("file_path", d.FilePath))
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Failed to upload file from S3. Please check if the file exists and you have proper access.",
			"code":    fiber.StatusBadRequest,
		})
	}

	time.Sleep(2 * time.Second) // wait for a while to ensure data is committed

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
	dataset, err := h.datasetSvc.UpdateWithTx(storeTx, d.ID, &models.UpdateDatasetParams{
		FilePath:  body.FilePath,
		RowCount:  int(count),
		Size:      res.Size,
		Columns:   columns,
		UpdatedBy: userID,
		OrgID:     orgID,
	})
	if err != nil {
		h.logger.Error("Error updating dataset record", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error updating dataset record",
			"code":    fiber.StatusInternalServerError,
		})
	}

	err = h.datasetSvc.DeleteSummaryWithTx(storeTx, res.TableName)
	if err != nil {
		h.logger.Error("Error deleting existing dataset summary", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error deleting existing dataset summary",
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

	summary, err := h.datasetSvc.CreateSummaryWithTx(storeTx, res.TableName, datasetSummary)
	if err != nil {
		h.logger.Error("Error creating dataset summary", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   err.Error(),
			"message": "Error creating dataset summary",
			"code":    fiber.StatusInternalServerError,
		})
	}

	err = h.aiAgentSvc.UploadSchema(&models.SchemaParams{
		DatasetID: d.ID,
		ProjectID: body.ProjectID,
	})
	if err != nil {
		h.logger.Error("Error uploading schema to AI agent", zap.Error(err))
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

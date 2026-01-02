package s3

import (
	"bufio"
	"context"
	"encoding/json"
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
// @Description Update an existing dataset with a new file from S3 with SSE progress updates
// @Tags s3
// @Accept json
// @Produce text/event-stream
// @Param body body updateRequestBody true "Update request parameters"
// @Success 200 {string} string "SSE stream of refresh progress"
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

	// Create SSE channel
	sseChan := make(chan SSEData, 10)

	// Helper to send SSE events
	sendEvent := func(eventType, message string, data any) {
		eventPayload := SSEEvent{
			Type:    eventType,
			Message: message,
			Data:    data,
		}
		payloadBytes, _ := json.Marshal(eventPayload)
		sseMessage := fmt.Sprintf("data: %s\n\n", payloadBytes)
		sseChan <- SSEData{Data: []byte(sseMessage)}
	}

	// Helper to handle failures
	handleFailure := func(failErr error) {
		errMsg := failErr.Error()
		errorPayload, _ := json.Marshal(map[string]string{"type": "error", "message": errMsg})
		errorMsg := fmt.Sprintf("event: error\ndata: %s\n\n", errorPayload)
		sseChan <- SSEData{Data: []byte(errorMsg)}
	}

	// Start async refresh process
	go func() {
		defer close(sseChan)
		txCtx := context.Background()

		sendEvent("status_update", "Validating dataset...", nil)

		// Check if dataset exists
		d, err := h.datasetSvc.GetByTableName(body.DatasetName, orgID)
		if err != nil {
			if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
				h.logger.Error("Dataset not found", zap.Error(err), zap.String("dataset_id", body.DatasetName))
				handleFailure(fmt.Errorf("dataset with name %s not found", body.DatasetName))
				return
			}
			h.logger.Error("Error fetching dataset", zap.Error(err), zap.String("dataset_id", body.DatasetName))
			handleFailure(fmt.Errorf("error validating dataset: %w", err))
			return
		}

		h.logger.Info("Dataset found, proceeding with update", zap.String("dataset_id", d.ID), zap.String("table_name", d.Name))

		sendEvent("status_update", "Starting database transactions...", nil)

		olapDB := h.olapSvc.GetDB()
		storeDB := h.datasetSvc.GetDB()

		olapTx, err := olapDB.Begin()
		if err != nil {
			h.logger.Error("Error starting OLAP transaction", zap.Error(err))
			handleFailure(fmt.Errorf("error starting OLAP transaction: %w", err))
			return
		}

		storeTx, err := storeDB.Begin(txCtx)
		if err != nil {
			h.logger.Error("Error starting Store transaction", zap.Error(err))
			olapTx.Rollback()
			handleFailure(fmt.Errorf("error starting Store transaction: %w", err))
			return
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

		sendEvent("status_update", "Dropping existing OLAP table...", nil)

		err = h.olapSvc.DropTableWithTx(olapTx, d.Name)
		if err != nil {
			h.logger.Error("Error dropping existing OLAP table", zap.Error(err), zap.String("table_name", d.Name))
			handleFailure(fmt.Errorf("error dropping existing OLAP table: %w", err))
			return
		}

		h.logger.Info("Starting file update", zap.String("file_path", d.FilePath), zap.String("dataset_id", d.ID))

		// override file path if provided
		if body.FilePath != "" {
			d.FilePath = body.FilePath
		}

		sendEvent("status_update", "Ingesting file from S3...", nil)

		// Upload file to OLAP service
		res, err := h.olapSvc.IngestS3File(olapTx, txCtx, d.FilePath, d.Name, nil, body.IgnoreErrors)
		if err != nil {
			h.logger.Error("Error uploading file to OLAP service", zap.Error(err), zap.String("file_path", d.FilePath))
			handleFailure(fmt.Errorf("failed to upload file from S3: %w", err))
			return
		}

		sendEvent("status_update", "Waiting for data to commit...", nil)
		time.Sleep(2 * time.Second) // wait for a while to ensure data is committed

		sendEvent("status_update", "Fetching dataset metrics...", nil)

		count, columns, err := h.getMetrics(res.TableName)
		if err != nil {
			h.logger.Error("Error fetching dataset metrics", zap.Error(err), zap.String("table_name", res.TableName))
			handleFailure(fmt.Errorf("error fetching dataset metrics: %w", err))
			return
		}

		sendEvent("status_update", "Updating dataset record...", nil)

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
			handleFailure(fmt.Errorf("error updating dataset record: %w", err))
			return
		}

		sendEvent("status_update", "Deleting old dataset summary...", nil)

		err = h.datasetSvc.DeleteSummaryWithTx(storeTx, res.TableName)
		if err != nil {
			h.logger.Error("Error deleting existing dataset summary", zap.Error(err))
			handleFailure(fmt.Errorf("error deleting existing dataset summary: %w", err))
			return
		}

		sendEvent("status_update", "Generating new dataset summary...", nil)

		datasetSummary, err := h.olapSvc.GetDatasetSummary(res.TableName)
		if err != nil {
			h.logger.Error("Error fetching dataset summary", zap.Error(err))
			handleFailure(fmt.Errorf("error fetching dataset summary: %w", err))
			return
		}

		sendEvent("status_update", "Saving dataset summary...", nil)

		summary, err := h.datasetSvc.CreateSummaryWithTx(storeTx, res.TableName, datasetSummary)
		if err != nil {
			h.logger.Error("Error creating dataset summary", zap.Error(err))
			handleFailure(fmt.Errorf("error creating dataset summary: %w", err))
			return
		}

		sendEvent("status_update", "Uploading schema to AI agent...", nil)

		err = h.aiAgentSvc.UploadSchema(&models.SchemaParams{
			DatasetID: d.ID,
			ProjectID: body.ProjectID,
		})
		if err != nil {
			h.logger.Error("Error uploading schema to AI agent", zap.Error(err))
			handleFailure(fmt.Errorf("error uploading schema to AI agent: %w", err))
			return
		}

		h.logger.Info("File update completed successfully",
			zap.String("dataset_id", dataset.ID))

		// Send completion event with dataset and summary
		sendEvent("complete", "Dataset refreshed successfully", map[string]any{
			"dataset": dataset,
			"summary": summary,
		})
	}()

	// Set SSE headers
	ctx.Set("Content-Type", "text/event-stream")
	ctx.Set("Cache-Control", "no-cache")
	ctx.Set("Connection", "keep-alive")
	ctx.Set("Transfer-Encoding", "chunked")

	// Stream SSE events to client
	ctx.Response().SetBodyStreamWriter(func(w *bufio.Writer) {
		for sse := range sseChan {
			if sse.Error != nil {
				h.logger.Error("Error received from stream source", zap.Error(sse.Error))
				return
			}

			if _, err := w.Write(sse.Data); err != nil {
				h.logger.Error("Error writing to client stream", zap.Error(err))
				return
			}

			if err := w.Flush(); err != nil {
				h.logger.Error("Error flushing client stream", zap.Error(err))
				return
			}
		}
	})

	return nil
}

package s3

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

// SSEEvent represents a server-sent event for S3 upload progress
type SSEEvent struct {
	Type    string `json:"type"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

// SSEData holds either data or error for SSE channel
type SSEData struct {
	Data  []byte
	Error error
}

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
		deleteErr := h.datasetSvc.Delete(rc.datasetID, rc.orgID)
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
// @Description Upload a file from S3 and create a new dataset with SSE progress updates
// @Tags s3
// @Accept json
// @Produce text/event-stream
// @Param body body uploadRequestBody true "Upload request parameters"
// @Success 200 {string} string "SSE stream of upload progress"
// @Failure 400 {object} responses.ErrorResponse "Invalid request body or S3 file access error"
// @Failure 404 {object} responses.ErrorResponse "Project not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /source/s3/upload [post]
func (h *httpHandler) upload(ctx *fiber.Ctx) error {
	orgID := ctx.Get(middleware.OrganizationIDHeader)
	userID := ctx.Get(middleware.UserCtxKey)
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

	// Start async upload process
	go func() {
		defer close(sseChan)
		ctxBg := context.Background()

		sendEvent("status_update", "Validating project...", nil)

		// Check if project exists
		project, err := h.projectSvc.Details(body.ProjectID, orgID)
		if err != nil {
			if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
				h.logger.Error("Project not found", zap.Error(err), zap.String("project_id", body.ProjectID))
				handleFailure(fmt.Errorf("project with ID %s not found", body.ProjectID))
				return
			}
			h.logger.Error("Error fetching project", zap.Error(err), zap.String("project_id", body.ProjectID))
			handleFailure(fmt.Errorf("error validating project: %w", err))
			return
		}

		h.logger.Info("Starting file upload", zap.String("file_path", body.FilePath), zap.String("project_id", project.ID))

		sendEvent("status_update", "Ingesting file from S3...", nil)

		// Upload file to OLAP service
		res, err := h.olapSvc.IngestS3File(nil, ctxBg, body.FilePath, "", body.AlterColumnNames, body.IgnoreErrors)
		if err != nil {
			h.logger.Error("Error uploading file to OLAP service", zap.Error(err), zap.String("file_path", body.FilePath))
			handleFailure(fmt.Errorf("failed to upload file from S3: %w", err))
			return
		}

		// Initialize cleanup resource object
		cleanup := resourceCleanup{
			tableName: res.TableName,
		}

		sendEvent("status_update", "Fetching dataset metrics...", nil)

		count, columns, err := h.getMetrics(res.TableName)
		if err != nil {
			h.logger.Error("Error fetching dataset metrics", zap.Error(err), zap.String("table_name", res.TableName))
			h.cleanupResources(cleanup)
			handleFailure(fmt.Errorf("error fetching dataset metrics: %w", err))
			return
		}

		sendEvent("status_update", "Creating dataset record...", nil)

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
			handleFailure(fmt.Errorf("error creating dataset record: %w", err))
			return
		}

		// Update cleanup object to include dataset info
		cleanup.hasDataset = true
		cleanup.datasetID = dataset.ID
		cleanup.orgID = dataset.OrgID

		sendEvent("status_update", "Generating dataset summary...", nil)

		datasetSummary, err := h.olapSvc.GetDatasetSummary(res.TableName)
		if err != nil {
			h.logger.Error("Error fetching dataset summary", zap.Error(err))
			h.cleanupResources(cleanup)
			handleFailure(fmt.Errorf("error fetching dataset summary: %w", err))
			return
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

		sendEvent("status_update", "Saving dataset summary...", nil)

		summary, err := h.datasetSvc.CreateDatasetSummary(res.TableName, datasetSummary)
		if err != nil {
			h.logger.Error("Error creating dataset summary", zap.Error(err))
			h.cleanupResources(cleanup)
			handleFailure(fmt.Errorf("error creating dataset summary: %w", err))
			return
		}

		// Update cleanup object to include summary info
		cleanup.hasSummary = true

		sendEvent("status_update", "Uploading schema to AI agent...", nil)

		err = h.aiAgentSvc.UploadSchema(&models.SchemaParams{
			DatasetID: dataset.ID,
			ProjectID: project.ID,
		})
		if err != nil {
			h.logger.Error("Error uploading schema to AI agent", zap.Error(err))
			h.cleanupResources(cleanup)
			handleFailure(fmt.Errorf("error uploading schema to AI agent: %w", err))
			return
		}

		h.logger.Info("File upload completed successfully",
			zap.String("dataset_id", dataset.ID),
			zap.String("project_id", project.ID))

		// Send completion event with dataset and summary
		sendEvent("complete", "Dataset created successfully", map[string]any{
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

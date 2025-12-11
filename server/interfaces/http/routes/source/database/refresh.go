package database

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/factly/gopie/domain"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg"
	"github.com/factly/gopie/interfaces/http/middleware"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

type refreshRequestBody struct {
	ProjectID   string `json:"project_id" validate:"required,uuid" example:"550e8400-e29b-41d4-a716-446655440000"`
	DatasetName string `json:"dataset_name" validate:"required,min=3" example:"gp_asdfghjklqwerty"`
	RefreshType string `json:"refresh_type" validate:"required,oneof=full incremental" example:"full"`
}

// @Summary Update dataset from database source
// @Description Updates an existing dataset from a database source by re-executing the source query and refreshing metrics, columns, row count, summary, and schema embedding with SSE progress updates
// @Tags database
// @Accept json
// @Produce text/event-stream
// @Param body body updateRequestBody true "Update request parameters"
// @Success 200 {string} string "SSE stream of refresh progress"
// @Failure 400 {object} responses.ErrorResponse "Invalid request body or database connection error"
// @Failure 404 {object} responses.ErrorResponse "Project or dataset not found"
// @Failure 500 {object} responses.ErrorResponse "Internal server error"
// @Router /source/database/refresh [post]
func (h *httpHandler) refresh(ctx *fiber.Ctx) error {
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)
	userID := ctx.Locals(middleware.UserCtxKey).(string)

	// Get request body from context
	var body refreshRequestBody
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

	// Start async refresh process
	go func() {
		defer close(sseChan)

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

		sendEvent("status_update", "Validating dataset...", nil)

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

		sendEvent("status_update", "Fetching database source configuration...", nil)

		source, err := h.dbSourceSvc.Get(d.ID, orgID)
		if err != nil {
			if domain.IsStoreError(err) && err == domain.ErrRecordNotFound {
				h.logger.Error("Database source not found for dataset", zap.Error(err), zap.String("dataset_id", d.ID))
				handleFailure(fmt.Errorf("database source for dataset ID %s not found", d.ID))
				return
			}
			h.logger.Error("Error fetching database source for dataset", zap.Error(err), zap.String("dataset_id", d.ID))
			handleFailure(fmt.Errorf("error validating database source: %w", err))
			return
		}

		h.logger.Info("updating database source dataset", zap.String("project_id", project.ID))

		tableName := d.Name

		var driver string

		if strings.HasPrefix(source.ConnectionString, "postgres") {
			driver = "postgres"
		} else {
			driver = "mysql"
		}

		var t time.Time
		if body.RefreshType == "incremental" && source.TimestampColumn != "" {
			t, err = time.Parse(time.RFC3339Nano, source.LastUpdatedAt)
			if err != nil {
				h.logger.Error("Error parsing last updated at timestamp", zap.Error(err), zap.String("timestamp", source.LastUpdatedAt))
				handleFailure(fmt.Errorf("error parsing last updated at timestamp: %w", err))
				return
			}
		}

		if body.RefreshType == "incremental" && source.TimestampColumn == "" {
			h.logger.Error("Timestamp column is required for incremental refresh", zap.String("dataset_id", d.ID))
			handleFailure(fmt.Errorf("timestamp column is required for incremental refresh"))
			return
		}

		sendEvent("status_update", fmt.Sprintf("Performing %s refresh from %s database...", body.RefreshType, driver), nil)

		refreshErr := func() error {
			if driver == "postgres" {
				if body.RefreshType == "incremental" && source.TimestampColumn != "" {
					return h.olapSvc.IncrementalRefreshPostgres(source.ConnectionString, source.SQLQuery, tableName, source.TimestampColumn, &t)
				}
				return h.olapSvc.FullTableRefreshPostgres(source.ConnectionString, source.SQLQuery, tableName)
			}
			if body.RefreshType == "incremental" && source.TimestampColumn != "" {
				return h.olapSvc.IncrementalRefreshMySQL(source.ConnectionString, source.SQLQuery, tableName, source.TimestampColumn, &t)
			}
			return h.olapSvc.FullTableRefreshMySQL(source.ConnectionString, source.SQLQuery, tableName)
		}()

		if refreshErr != nil {
			var msg string
			if body.RefreshType == "incremental" && source.TimestampColumn != "" {
				if driver == "postgres" {
					msg = "error performing incremental refresh from postgres"
				} else {
					msg = "error performing incremental refresh from mysql"
				}
			} else {
				if driver == "postgres" {
					msg = "error creating table from postgres"
				} else {
					msg = "error creating table from mysql"
				}
			}
			h.logger.Error(msg, zap.Error(refreshErr))
			handleFailure(fmt.Errorf("%s: %w", msg, refreshErr))
			return
		}

		if body.RefreshType == "incremental" && source.TimestampColumn != "" {
			sendEvent("status_update", "Updating timestamp for incremental refresh...", nil)
			lastUpdatedAt, err := h.olapSvc.GetLatestTimestamp(tableName, source.TimestampColumn)
			if err != nil {
				h.logger.Error("Error fetching latest timestamp from OLAP", zap.Error(err), zap.String("table_name", tableName), zap.String("timestamp_column", source.TimestampColumn))
				handleFailure(fmt.Errorf("error fetching latest timestamp from OLAP: %w", err))
				return
			}
			if lastUpdatedAt != nil {
				err = h.dbSourceSvc.Update(context.Background(), models.UpdateDatabaseSourceLastUpdatedAtParams{
					ID:            source.ID,
					LastUpdatedAt: *lastUpdatedAt,
				})
				if err != nil {
					h.logger.Error("Error updating database source timestamp", zap.Error(err))
					handleFailure(fmt.Errorf("error updating database source timestamp: %w", err))
					return
				}
			}
		}

		sendEvent("status_update", "Waiting for data commit...", nil)
		time.Sleep(2 * time.Second) // Wait for the table to be created in OLAP

		sendEvent("status_update", "Fetching dataset metrics...", nil)

		count, columns, err := h.getMetrics(tableName)
		if err != nil {
			h.logger.Error("Error fetching dataset metrics", zap.Error(err), zap.String("table_name", tableName))
			handleFailure(fmt.Errorf("error fetching dataset metrics: %w", err))
			return
		}

		sendEvent("status_update", "Updating dataset record...", nil)

		dataset, err := h.datasetSvc.Update(d.ID, &models.UpdateDatasetParams{
			RowCount:  count,
			Columns:   columns,
			UpdatedBy: userID,
			OrgID:     orgID,
		})
		if err != nil {
			h.logger.Error("Error updating dataset record", zap.Error(err))
			handleFailure(fmt.Errorf("error updating dataset record: %w", err))
			return
		}

		sendEvent("status_update", "Generating dataset summary...", nil)

		datasetSummary, err := h.olapSvc.GetDatasetSummary(tableName)
		if err != nil {
			h.logger.Error("Error fetching dataset summary", zap.Error(err))
			handleFailure(fmt.Errorf("error fetching dataset summary: %w", err))
			return
		}

		sendEvent("status_update", "Saving dataset summary...", nil)

		summary, err := h.datasetSvc.CreateDatasetSummary(tableName, datasetSummary)
		if err != nil {
			h.logger.Error("Error creating dataset summary", zap.Error(err))
			handleFailure(fmt.Errorf("error creating dataset summary: %w", err))
			return
		}

		sendEvent("status_update", "Uploading schema to AI agent...", nil)

		err = h.aiAgentSvc.UploadSchema(&models.SchemaParams{
			DatasetID: dataset.ID,
			ProjectID: project.ID,
		})
		if err != nil {
			h.logger.Error("Error uploading schema to AI agent", zap.Error(err))
			handleFailure(fmt.Errorf("error uploading schema to AI agent: %w", err))
			return
		}

		h.logger.Info("Database source dataset refresh completed successfully",
			zap.String("dataset_id", dataset.ID),
			zap.String("project_id", project.ID),
			zap.String("table_name", tableName))

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

package routes

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"strconv"

	"github.com/factly/gopie/downlods-server/models"
	"github.com/factly/gopie/downlods-server/queue"
	"github.com/factly/gopie/downlods-server/server/middleware"
	"github.com/gofiber/fiber/v2"
	"github.com/valyala/fasthttp"
	"go.uber.org/zap"
)

// createDownload creates a new download job
// @Summary Create a new download job
// @Description Submit a SQL query to create a new download job. Returns Server-Sent Events (SSE) stream for real-time progress updates.
// @Tags Downloads
// @Accept json
// @Produce text/event-stream
// @Param x-user-id header string true "User ID from authentication"
// @Param x-organization-id header string true "Organization ID from authentication"
// @Param request body models.CreateDownloadRequest true "Download request"
// @Success 200 {string} string "SSE stream with download progress"
// @Failure 400 {object} map[string]string "Invalid request body"
// @Security BearerAuth
// @Router /downloads [post]
func (h *httpHandler) createDownload(ctx *fiber.Ctx) error {
	userID := ctx.Locals(middleware.UserCtxKey).(string)
	orgID := ctx.Locals(middleware.OrganizationCtxKey).(string)
	var req models.CreateDownloadRequest
	if err := ctx.BodyParser(&req); err != nil {
		return ctx.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid request body"})
	}
	req.OrgID = orgID
	req.UserID = userID

	ctx.Set("Content-Type", "text/event-stream")
	ctx.Set("Cache-Control", "no-cache")
	ctx.Set("Connection", "keep-alive")

	ctxDone := ctx.Context().Done()

	ctx.Context().SetBodyStreamWriter(fasthttp.StreamWriter(func(w *bufio.Writer) {
		fmt.Fprintf(w, "event: request_received\ndata: {\"message\": \"Request received, preparing to submit to queue...\"}\n\n")
		w.Flush()

		bgCtx := context.Background()

		downloadJob, err := h.queue.Submit(bgCtx, &req)
		if err != nil {
			h.logger.Error("Failed to submit download job", zap.Error(err))
			errorEvent, _ := json.Marshal(map[string]string{"type": "error", "message": "could not create download job"})
			fmt.Fprintf(w, "event: error\ndata: %s\n\n", errorEvent)
			w.Flush()
			return
		}
		downloadID := downloadJob.ID.String()

		clientChan := h.queue.Manager.Subscribe(downloadID)
		defer h.queue.Manager.Unsubscribe(downloadID, clientChan)

		event, _ := json.Marshal(downloadJob)
		fmt.Fprintf(w, "event: job_created\ndata: %s\n\n", event)
		w.Flush()

		for {
			select {
			case event, ok := <-clientChan:
				if !ok {
					return // Channel closed
				}
				fmt.Fprintf(w, "data: %s\n\n", event)
				if err := w.Flush(); err != nil {
					h.logger.Info("SSE stream writer flush error", zap.Error(err), zap.String("download_id", downloadID))
					return
				}

				var eventData queue.ProgressEvent
				if err := json.Unmarshal([]byte(event), &eventData); err == nil {
					if eventData.Type == "complete" || eventData.Type == "error" {
						h.logger.Info("SSE stream finished, closing connection.", zap.String("download_id", downloadID), zap.String("reason", eventData.Type))
						return
					}
				}
			case <-ctxDone:
				h.logger.Info("SSE client disconnected", zap.String("download_id", downloadID))
				return
			}
		}
	}))

	return nil
}

// listDownloads retrieves a paginated list of all download jobs for the user.
// @Summary List download jobs
// @Description Retrieve a paginated list of all download jobs for the authenticated user
// @Tags Downloads
// @Produce json
// @Param x-user-id header string true "User ID from authentication"
// @Param x-organization-id header string true "Organization ID from authentication"
// @Param limit query int false "Number of items to return" default(10) minimum(1) maximum(100)
// @Param offset query int false "Number of items to skip" default(0) minimum(0)
// @Success 200 {array} models.Download "List of download jobs"
// @Failure 500 {object} map[string]string "Internal server error"
// @Security BearerAuth
// @Router /downloads [get]
func (h *httpHandler) listDownloads(c *fiber.Ctx) error {
	userID := c.Get("x-user-id")
	orgID := c.Get("x-organization-id")

	limit, _ := strconv.Atoi(c.Query("limit", "10"))
	offset, _ := strconv.Atoi(c.Query("offset", "0"))

	downloads, err := h.queue.DbStore.ListDownloadsByUser(c.Context(), userID, orgID, int32(limit), int32(offset))
	if err != nil {
		h.logger.Error("Failed to list downloads", zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "could not retrieve downloads"})
	}

	return c.JSON(downloads)
}

// getDownload retrieves the details of a single download job.
// @Summary Get download job details
// @Description Retrieve the details of a specific download job
// @Tags Downloads
// @Produce json
// @Param id path string true "Download job ID"
// @Param x-organization-id header string true "Organization ID from authentication"
// @Success 200 {object} models.Download "Download job details"
// @Failure 404 {object} map[string]string "Download not found"
// @Security BearerAuth
// @Router /downloads/{id} [get]
func (h *httpHandler) getDownload(c *fiber.Ctx) error {
	downloadID := c.Params("id")
	orgID := c.Get("x-organization-id")

	download, err := h.queue.DbStore.GetDownload(c.Context(), downloadID, orgID)
	if err != nil {
		h.logger.Error("Failed to get download", zap.String("id", downloadID), zap.Error(err))
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "download not found"})
	}

	return c.JSON(download)
}

// deleteDownload deletes a download job record.
// @Summary Delete download job
// @Description Delete a download job record and associated data
// @Tags Downloads
// @Param id path string true "Download job ID"
// @Param x-organization-id header string true "Organization ID from authentication"
// @Success 204 "Download successfully deleted"
// @Failure 500 {object} map[string]string "Internal server error"
// @Security BearerAuth
// @Router /downloads/{id} [delete]
func (h *httpHandler) deleteDownload(c *fiber.Ctx) error {
	downloadID := c.Params("id")
	orgID := c.Get("x-organization-id")

	err := h.queue.DbStore.DeleteDownload(c.Context(), downloadID, orgID)
	if err != nil {
		h.logger.Error("Failed to delete download", zap.String("id", downloadID), zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "could not delete download"})
	}

	return c.SendStatus(fiber.StatusNoContent)
}
